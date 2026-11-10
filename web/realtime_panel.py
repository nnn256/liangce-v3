"""Fresh market panels. Closed bars alone enter structural analysis.

Provider prices are kept separate from the verified historical archive. This
module never replaces an archive or certifies provider adjustment as verified.
"""
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
import bisect
import calendar
import hashlib
import json
import threading
import time

from fastapi import HTTPException

CN=timezone(timedelta(hours=8))
NATIVE={'1m':'1m','5m':'5m','15m':'15m','30m':'30m','60m':'60m','day':'1D','week':'1W','month':'1M','quarter':'quarter','year':'year','5d':'5d',
        'timeshare':'1m','five_days':'1m'}
cache=OrderedDict()
cache_lock=threading.Lock()
scan_pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='period-scan')
scan_lock=threading.Lock()
scans={}
observations=OrderedDict()


def trading_hours(now):
    minute=now.hour*60+now.minute
    return now.weekday()<5 and (555<=minute<=690 or 780<=minute<=900)


def close_time(label,period):
    stamp=str(label).replace(' ','T')
    point=datetime.fromisoformat(stamp)
    if point.tzinfo is None:point=point.replace(tzinfo=CN)
    else:point=point.astimezone(CN)
    if period.endswith('m'):return point
    day=point.date()
    if period=='week':day+=timedelta(days=4-day.weekday())
    elif period in {'month','quarter','year'}:
        month=day.month if period=='month' else ((day.month-1)//3+1)*3 if period=='quarter' else 12
        day=day.replace(month=month,day=calendar.monthrange(day.year,month)[1])
        while day.weekday()>4:day-=timedelta(days=1)
    return datetime.combine(day,datetime.min.time(),tzinfo=CN).replace(hour=15)


def provider_bars(rows,period,now):
    from chanmodel.model import Candle
    result=[];last=None
    for row in rows:
        close=close_time(row['time'],period)
        # Intraday providers may supply the not-yet-closed current interval.
        if period.endswith('m') and close>now+timedelta(minutes=int(period[:-1])):continue
        if not period.endswith('m') and str(row['time'])[:10]>now.date().isoformat():continue
        if close==last:continue
        if last and close<last:raise ValueError('行情K线时间顺序异常')
        result.append(Candle(len(result),*[float(row[key]) for key in ['open','high','low','close']],
                             close.isoformat(),float(row.get('volume',0))*100,close<=now))
        last=close
    return result


def make_panel(code,period,candles,now,metadata=None):
    from chanmodel.complete_study import analyze_complete
    from chanmodel.causal_replay import abcd_objects,source_rule_audit
    from chanmodel.model import Config
    from chanmodel.signals import macd
    closed=[bar for bar in candles if bar.closed]
    if not candles:raise HTTPException(503,'上游未返回真实K线，无法计算结构')
    if not closed:raise HTTPException(503,'尚无已收盘K线，无法计算结构；不生成假买卖点')
    metadata=metadata or {'source':'stock-dashboard/market_gateway','adjustment':'provider_unspecified',
                           'price_unit':'CNY','volume_unit':'shares','scope':'provider_recent_history'}
    digest=hashlib.sha256(json.dumps([[b.closed_at,b.open,b.high,b.low,b.close,b.volume] for b in closed]).encode()).hexdigest()
    report=analyze_complete(code,period,closed,now.isoformat(),digest)
    from chanmodel.stroke_signals import snapshot as fine_snapshot
    fine=fine_snapshot(closed)
    fine['confirmations']=[];fine['confirmation_records']=[]
    closed_times=[bar.closed_at for bar in closed]
    for point in fine['signals']:
        passed=point['rule_audit']['passed'] and point['state']!='invalidated'
        record={'id':point['id'],'state':'confirmed' if passed else point['state'],'first_seen_at':now.isoformat()}
        if passed:
            key=('stroke',code,period,point['class'],point['event_time'],point['price'])
            witness=observations.setdefault(key,{'time':now.isoformat(),'index':len(closed)-1})
            record.update(first_seen_at=witness['time'],confirmed_at=witness['time'])
            fine['confirmations'].append({'signal_id':point['id'],'class':point['class'],'side':point['side'],'rank':0,
                'resolution':'stroke','anchor':point['anchor'],'anchor_time':point['event_time'],'price':point['price'],
                'observed_index':max(0,bisect.bisect_right(closed_times,witness['time'])-1),'observed_at':witness['time'],'confirmed_at':witness['time'],
                'event':'confirmed','point':point,'execution_allowed':False,
                'confirmation_semantics':'stroke_rule_current_observation; earliest_historical_confirmation_not_claimed'})
        fine['confirmation_records'].append(record)
    while len(observations)>2000:observations.popitem(last=False)
    confirmations=[];records=[];report['as_of_index']=len(closed)-1
    eligible=metadata.get('split_adjustment_verified') is True
    for point in report['signals']:
        audit=source_rule_audit(point,report)
        audit['gates']['data_adjustment_verified']=eligible
        audit['missing']=[key for key,value in audit['gates'].items() if not value]
        audit['passed']=not audit['missing']
        point['rule_audit']=audit
        state='confirmed' if audit['passed'] else point['state']
        record={'id':point['id'],'state':state,'current_state':state,'first_seen_at':now.isoformat(),
                'confirmed_at':now.isoformat() if audit['passed'] else None,'audit':audit}
        records.append(record)
        if audit['passed']:
            ident=(code,period,point['id'],point['price'])
            witnessed=observations.setdefault(ident,{'time':now.isoformat(),'index':len(closed)-1})
            observations.move_to_end(ident)
            while len(observations)>2000:observations.popitem(last=False)
            record['first_seen_at']=witnessed['time'];record['confirmed_at']=witnessed['time']
            confirmations.append({'signal_id':point['id'],'class':point['class'],'side':point['side'],'rank':point['rank'],
                                  'anchor':point['anchor'],'anchor_time':point['event_time'],'price':point['price'],
                                  'observed_index':witnessed['index'],'observed_at':witnessed['time'],'confirmed_at':witnessed['time'],
                                  'event':'confirmed','rule_audit':audit,'point':point,'execution_allowed':False,
                                  'confirmation_semantics':'current_observation_only; earliest_historical_confirmation_not_claimed'})
    signal_types=['first_buy','second_buy','third_buy','first_sell','second_sell','third_sell']
    diagnostics={kind:{'candidates':sum(point['class']==kind for point in report['signals']),
                       'confirmed':sum(point['class']==kind for point in confirmations),
                       'reason':'已按本周期完整数据计算；只有满足同级结构的点位才会产生' if report['signals'] else '当前可得数据尚未形成完整线段/中枢/趋势与回试结构',
                       'bars':len(closed),'segments':len(report['base']['segments']),
                       'centers':sum(len(layer['centers']) for layer in report['hierarchy']['levels'])} for kind in signal_types}
    bars=[{'time':int(datetime.fromisoformat(b.closed_at).timestamp())+8*3600,
           'source_index':b.pos,'date_cn':b.closed_at[:16].replace('T',' '),
           'open':b.open,'high':b.high,'low':b.low,'close':b.close,'volume':b.volume,'is_closed':b.closed} for b in candles]
    from web.research_api import local_symbols
    name=next((item['name'] for item in local_symbols() if item['symbol']==code),code)
    observed=min(datetime.fromisoformat(candles[-1].closed_at),now).isoformat()
    return {'schema':'liangce.research.v1','symbol':code,'name':name,'period':period,'label':period,
            'resolution':'segment','stroke_model':fine,
            'kind':'candles','bars':bars,
            'coverage':{'count':len(bars),'closed_count':len(closed),'forming_count':len(bars)-len(closed),
                        'first':bars[0]['date_cn'],'last':observed[:16].replace('T',' '),'input_sha256':digest,
                        'source':metadata['source'],'scope':metadata.get('scope','provider_recent_history'),
                        'source_rows':metadata.get('source_rows',len(bars)),'source_retention_unlimited':False},
            **{key:report[key] for key in ['profile','definition_mode','approximation_loss','decompositions','divergence_comparisons','center_evolution']},
            **{key:report['base'][key] for key in ['fractals','merged','strokes','segments']},
            'all_centers':[c for layer in report['hierarchy']['levels'] for c in layer['centers']],
            'signals':report['signals'],'divergences':report['divergence_comparisons'],'monitors':report['center_monitors'],
            'features':report['feature_sequences'],'abcd':abcd_objects(report),
            'macd':[dict(time=bars[index]['time'],**value) for index,value in enumerate(macd(candles,Config(macd_multiplier=2)))],
            'confirmations':confirmations,'signal_events':[],'confirmation_records':records,'signal_diagnostics':diagnostics,'portfolio_metrics':None,
            'portfolio_trades':[],'portfolio_equity':[],'source_kind':'live_market_panel',
            'provenance':{**metadata,'confirmation_eligible':eligible,'forming_bars_used_for_structure':False},
            'data_as_of':observed,'structure_as_of':closed[-1].closed_at,
            'computed_at':now.isoformat(),'fetched_at':now.isoformat(),
            'raw_last_price':metadata.get('raw_last_price'),'analysis_last_price':closed[-1].close,
            'adjustment_note':'已核验转增事件的因果后复权；原始成交价另列' if eligible else '行情源复权口径未认证，结构候选与确认分别检查',
            'refresh_after_seconds':15 if trading_hours(now) else 300,
            'market_session':'trading_hours' if trading_hours(now) else 'outside_trading_hours',
            'execution_allowed':False,'strict_original_equivalence_proven':False,
            'backtest_scope_note':'实时确认是当前证据可见时刻，不倒填为历史最早确认；历史因果确认与成交回测请切换历史研究'}


def live_panel(code,period,*,refresh=False):
    if period=='auction':
        from web.auction_panel import auction_panel
        return auction_panel(code,refresh)
    if period not in NATIVE:raise HTTPException(422,'分时/集合竞价价格快照不具备连续OHLC证据；可查看对应数据，买卖点需选择K线周期')
    now=datetime.now(CN);ttl=10 if trading_hours(now) else 60
    key=(code,period)
    with cache_lock:
        entry=cache.get(key)
        if entry and not refresh and time.monotonic()-entry[0]<ttl:
            cache.move_to_end(key);return entry[1]
        import market_gateway as mg
        try:
            from web import tdx_provider
            if tdx_provider.enabled():
                bars,metadata=tdx_provider.fetch(code,'1m' if period in {'timeshare','five_days'} else period,now)
            else:
                if period in {'5d','quarter','year'}:raise HTTPException(503,'此周期需要TDX完整接口；请配置TDX数据源后计算，不以别的周期冒充')
                source=mg.fetch_symbol_klines(code[2:]+'.'+code[:2].upper(),NATIVE[period],refresh=True)
                bars=provider_bars(source.get('klines',[]),'1m' if period in {'timeshare','five_days'} else period,now);metadata=None
            panel=make_panel(code,'1m' if period in {'timeshare','five_days'} else period,bars,now,metadata)
            if period in {'timeshare','five_days'}:
                panel.update(period=period,label='分时（原生1分K计算结构）' if period=='timeshare' else '五日分时（原生1分K计算结构）',
                             kind='line',structural_ohlc=True,display_session_count=1 if period=='timeshare' else 5,
                             points=[{**bar,'value':bar['close']} for bar in panel['bars']])
                panel['provenance']['display_semantics']='line uses native minute close; signals use underlying complete OHLC history, never sampled prices'
        except HTTPException:raise
        except Exception as error:raise HTTPException(503,'实时K线暂不可用：'+str(error)[:160]) from error
        cache[key]=(time.monotonic(),panel);cache.move_to_end(key)
        while len(cache)>1:cache.popitem(last=False)
        return panel


def period_overview(code):
    now=time.monotonic()
    with scan_lock:
        prior=scans.get(code)
        if prior and (prior['state']=='running' or now-prior['started']<300):
            return {key:value for key,value in prior.items() if key!='started'}
        if any(item['state']=='running' for item in scans.values()):raise HTTPException(429,'全周期检查正在运行，请稍后重试')
        scans.clear();scans[code]={'symbol':code,'state':'running','completed':0,'total':11,'rows':[],'started':now}

    def run():
        for period in ['1m','5m','15m','30m','60m','day','5d','week','month','quarter','year']:
            try:
                panel=live_panel(code,period)
                row={'period':period,'bars':panel['coverage']['count'],'closed_bars':panel['coverage']['closed_count'],
                     'last':panel['coverage']['last'],'source':panel['provenance']['source'],
                     'signals':{key:value['candidates'] for key,value in panel['signal_diagnostics'].items()},
                     'confirmed':{key:value['confirmed'] for key,value in panel['signal_diagnostics'].items()},'state':'completed'}
            except Exception as error:row={'period':period,'state':'failed','error':str(error)[:240]}
            with scan_lock:
                current=scans[code];current['rows']=current['rows']+[row];current['completed']+=1
        with scan_lock:scans[code]['state']='completed'
    scan_pool.submit(run)
    return {'symbol':code,'state':'running','completed':0,'total':11,'rows':[]}
