"""Fresh market panels. Closed bars alone enter structural analysis.

Provider prices are kept separate from the verified historical archive. This
module never replaces an archive or certifies provider adjustment as verified.
"""
from collections import OrderedDict
from datetime import datetime,timedelta,timezone
import calendar
import hashlib
import json
import threading
import time

from fastapi import HTTPException

CN=timezone(timedelta(hours=8))
NATIVE={'1m':'1m','5m':'5m','15m':'15m','30m':'30m','60m':'60m','day':'1D','week':'1W','month':'1M'}
cache=OrderedDict()
cache_lock=threading.Lock()


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
    elif period=='month':
        day=day.replace(day=calendar.monthrange(day.year,day.month)[1])
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


def make_panel(code,period,candles,now):
    from chanmodel.complete_study import analyze_complete
    from chanmodel.causal_replay import abcd_objects
    from chanmodel.model import Config
    from chanmodel.signals import macd
    closed=[bar for bar in candles if bar.closed]
    if len(closed)<3:raise HTTPException(503,'上游未返回足够的已收盘K线，无法计算结构')
    digest=hashlib.sha256(json.dumps([[b.closed_at,b.open,b.high,b.low,b.close,b.volume] for b in closed]).encode()).hexdigest()
    report=analyze_complete(code,period,closed,now.isoformat(),digest)
    bars=[{'time':int(datetime.fromisoformat(b.closed_at).timestamp())+8*3600,
           'source_index':b.pos,'date_cn':b.closed_at[:16].replace('T',' '),
           'open':b.open,'high':b.high,'low':b.low,'close':b.close,'volume':b.volume,'is_closed':b.closed} for b in candles]
    from web.research_api import local_symbols
    name=next((item['name'] for item in local_symbols() if item['symbol']==code),code)
    observed=min(datetime.fromisoformat(candles[-1].closed_at),now).isoformat()
    return {'schema':'liangce.research.v1','symbol':code,'name':name,'period':period,'label':period,
            'kind':'candles','bars':bars,
            'coverage':{'count':len(bars),'closed_count':len(closed),'forming_count':len(bars)-len(closed),
                        'first':bars[0]['date_cn'],'last':observed[:16].replace('T',' '),'input_sha256':digest,
                        'source':'stock-dashboard/market_gateway','scope':'provider_recent_history'},
            **{key:report[key] for key in ['profile','definition_mode','approximation_loss','decompositions','divergence_comparisons','center_evolution']},
            **{key:report['base'][key] for key in ['fractals','merged','strokes','segments']},
            'all_centers':[c for layer in report['hierarchy']['levels'] for c in layer['centers']],
            'signals':report['signals'],'divergences':report['divergence_comparisons'],'monitors':report['center_monitors'],
            'features':report['feature_sequences'],'abcd':abcd_objects(report),
            'macd':[dict(time=bars[index]['time'],**value) for index,value in enumerate(macd(candles,Config(macd_multiplier=2)))],
            'confirmations':[],'signal_events':[],'confirmation_records':[],'portfolio_metrics':None,
            'portfolio_trades':[],'portfolio_equity':[],'source_kind':'live_market_panel',
            'provenance':{'source':'stock-dashboard/market_gateway','adjustment':'provider_unspecified',
                          'confirmation_eligible':False,'forming_bars_used_for_structure':False},
            'data_as_of':observed,'structure_as_of':closed[-1].closed_at,
            'computed_at':now.isoformat(),'fetched_at':now.isoformat(),
            'raw_last_price':None,'analysis_last_price':closed[-1].close,
            'adjustment_note':'行情源复权口径未认证；保持原生输入，不拼接已核验历史价格',
            'refresh_after_seconds':15 if trading_hours(now) else 300,
            'market_session':'trading_hours' if trading_hours(now) else 'outside_trading_hours',
            'execution_allowed':False,'strict_original_equivalence_proven':False,
            'backtest_scope_note':'实时图表只更新结构候选；已核验确认与成交回测请切换历史研究'}


def live_panel(code,period):
    if period not in NATIVE:raise HTTPException(422,'此周期暂没有可靠的实时原生数据，请切换日K/分钟/周/月，或查看历史研究')
    now=datetime.now(CN);ttl=10 if trading_hours(now) else 60
    key=(code,period)
    with cache_lock:
        entry=cache.get(key)
        if entry and time.monotonic()-entry[0]<ttl:
            cache.move_to_end(key);return entry[1]
        import market_gateway as mg
        try:
            source=mg.fetch_symbol_klines(code[2:]+'.'+code[:2].upper(),NATIVE[period],refresh=True)
            bars=provider_bars(source.get('klines',[]),period,now)
            panel=make_panel(code,period,bars,now)
        except HTTPException:raise
        except Exception as error:raise HTTPException(503,'实时K线暂不可用：'+str(error)[:160]) from error
        cache[key]=(time.monotonic(),panel);cache.move_to_end(key)
        while len(cache)>3:cache.popitem(last=False)
        return panel
