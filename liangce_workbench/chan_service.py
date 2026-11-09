"""Causal six-class Chan analysis. Endpoints, observation and confirmation are separate."""
import collections
import copy
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import threading

from .chanmodel.model import Candle
from .chanmodel.causal_replay import StreamingStructure, SignalLedger

NAMES={'first_buy':'一买','second_buy':'二买','third_buy':'三买','first_sell':'一卖','second_sell':'二卖','third_sell':'三卖'}
PROFILE='chan_recursive_causal_v3_class_boundaries'
CN=dt.timezone(dt.timedelta(hours=8))

def as_of_time(value=None):
    if value is None:return dt.datetime.now(CN)
    text=str(value).replace(' ','T')
    parsed=dt.datetime.fromisoformat(text+'T23:59:59+08:00' if len(text)==10 else text)
    return parsed.replace(tzinfo=CN) if parsed.tzinfo is None else parsed.astimezone(CN)

def bar_time(value):
    text=str(value).replace(' ','T')
    parsed=dt.datetime.fromisoformat(text+'T15:00:00+08:00' if len(text)==10 else text)
    return parsed.replace(tzinfo=CN) if parsed.tzinfo is None else parsed.astimezone(CN)

def aggregate(rows,period,as_of=None):
    if period not in ('day','week','month'):raise ValueError('当前全市场取数支持日/周/月线')
    groups=[];cutoff=as_of_time(as_of)
    for b in rows:
        if b.get('is_closed') is False or bar_time(b['date'])>cutoff:continue
        day=dt.date.fromisoformat(b['date'][:10]);key=day.isoformat() if period=='day' else (day-dt.timedelta(days=day.weekday())).isoformat() if period=='week' else day.strftime('%Y-%m')
        if groups and groups[-1]['key']==key:
            x=groups[-1];x.update(date=b['date'],high=max(x['high'],b['high']),low=min(x['low'],b['low']),close=b['close'],volume=x['volume']+b['volume'])
        else:groups.append(dict(key=key,**{k:b[k] for k in ('date','open','high','low','close','volume')}))
    # Evaluate closure at the replay cutoff, never today's wall clock. A future
    # Friday must not change which bars were closed during a Wednesday replay.
    if period!='day':
        closed=[]
        for g in groups:
            last=dt.date.fromisoformat(g['date'][:10])
            if period=='week':end=last+dt.timedelta(days=4-last.weekday())
            else:
                following=last.replace(day=28)+dt.timedelta(days=4);end=following.replace(day=1)-dt.timedelta(days=1)
            if dt.datetime.combine(end,dt.time(15),CN)<=cutoff:closed.append(g)
        groups=closed
    return [{k:v for k,v in g.items() if k!='key'} for g in groups]

def simulate(bars,events,code,policy='confirmed',start=None,end=None):
    """Independent-stock research account; next-open orders, T+1, explicit costs."""
    if policy not in ('confirmed','candidate_experiment'):raise ValueError('Unknown backtest policy')
    code=str(code).removeprefix('sh').removeprefix('sz').removeprefix('bj')
    cash=100000.;position=None;pending=None;trades=[];orders=[];curve=[];peak=cash;maxdd=0;fees=0.
    by_index=collections.defaultdict(list)
    for event in events:by_index[event['observed_index']].append(event)
    def charge(side,value):return max(5.,value*.0003)+value*.00001+(value*.0005 if side=='sell' else 0)
    for i,b in enumerate(bars):
        date=b['date'][:10]
        if (start and date<start) or (end and date>end):continue
        current=by_index[i];rate=.3 if code.startswith(('4','8','92')) else .2 if code.startswith(('30','68')) else .1
        reference=bars[i-1]['close'] if i else None
        if pending and pending['index']<=i:
            side=pending['side'];reason=None
            if b['volume']<=0:reason='无成交量'
            if reference and side=='buy' and b['open']>=round(reference*(1+rate),2)-.005:reason='涨停开盘无法买入'
            if reference and side=='sell' and b['open']<=round(reference*(1-rate),2)+.005:reason='跌停开盘无法卖出'
            if side=='sell' and position and date<=position['entry_date']:reason='T+1限制'
            if side=='buy' and b['open']<=pending['invalidation']:reason='开盘已破失效价'
            price=round(b['open']*(1.0005 if side=='buy' else .9995),2)
            if not reason and side=='buy':
                risk=max(.01,price-pending['invalidation']);qty=min(math.floor(cash*.01/risk/100)*100,math.floor(cash*.2/price/100)*100)
                if qty<100:reason='风险预算不足一手'
                else:
                    fee=charge('buy',qty*price);cash-=qty*price+fee;fees+=fee
                    position=dict(code=code,entry_date=date,entry=price,shares=qty,cost=qty*price+fee,signal_id=pending['id'],signal_class=pending['class'],signal_time=pending['at'],invalidation=pending['invalidation'])
            elif not reason and side=='sell' and position:
                qty=position['shares'];fee=charge('sell',qty*price);cash+=qty*price-fee;fees+=fee
                trades.append({**position,'exit_date':date,'exit':price,'reason':pending['reason'],'pnl':qty*price-fee-position['cost'],'return_pct':(qty*price-fee)/position['cost']-1});position=None
            orders.append(dict(date=date,side=side,state='blocked' if reason else 'filled',reason=reason or pending.get('reason'),signal_time=pending['at']))
            if side=='buy' or not reason:pending=None
        accepted='confirmed' if policy=='confirmed' else 'candidate_observed'
        if position:
            revoked=any(e['signal_id']==position['signal_id'] and e['event'] in ('invalidated','withdrawn') for e in current)
            sale=any(e['event']==accepted and e['side']=='sell' for e in current)
            broken=b['low']<=position['invalidation']
            if pending is None and (revoked or sale or broken):pending=dict(side='sell',index=i+1,at=b['date'],reason='结构失效' if broken else '信号撤销' if revoked else '缠论卖点')
        elif pending is None:
            buy=next((e for e in current if e['event']==accepted and e['side']=='buy'),None)
            if buy:pending=dict(side='buy',index=i+1,id=buy['signal_id'],**{'class':buy['class']},at=buy['observed_at'],invalidation=buy['invalidation'])
        if pending and pending['side']=='buy' and any(e['signal_id']==pending['id'] and e['event'] in ('invalidated','withdrawn') for e in current):pending=None
        equity=cash+(position['shares']*b['close'] if position else 0);peak=max(peak,equity);dd=(peak-equity)/peak;maxdd=max(maxdd,dd);curve.append(dict(date=date,equity=equity,drawdown=dd))
    wins=sum(x['pnl']>0 for x in trades)
    return dict(policy=policy,initial_equity=100000,ending_equity=curve[-1]['equity'] if curve else 100000,total_return=(curve[-1]['equity']/100000-1) if curve else 0,max_drawdown=maxdd,completed_trades=len(trades),wins=wins,win_rate=wins/len(trades) if trades else None,total_fees=fees,trades=trades,orders=orders,equity=curve,open_position=position,execution_allowed=False,
        note='单股独立10万元研究账户；已确认事件后次根开盘，T+1/100股/佣金/印花税/滑点/开盘涨跌停限制。未接入除权派息和历史ST/上市日档案，收益不等于结构准确率。'+('仅候选实验，不表示已确认买卖点。' if policy!='confirmed' else ''))

def analyze(history,period='day',cutoff=None):
    source=history['bars'];asof=as_of_time(cutoff)
    rows=[copy.deepcopy(b) for b in source if b.get('is_closed') is not False and bar_time(b['date'])<=asof] if history.get('native_period')==period else aggregate(source,period,asof)
    if not rows:raise ValueError('该周期没有已闭合K线')
    stream=StreamingStructure();ledger=SignalLedger(period)
    for i,b in enumerate(rows):
        stamp=bar_time(b['date']).isoformat()
        candle=Candle(i,b['open'],b['high'],b['low'],b['close'],stamp,b['volume'],True)
        changed=stream.append(candle);ledger.invalidate(candle)
        if changed:ledger.observe(stream.snapshot(),candle,stream.bars)
    return finish_result(history,period,rows,stream,ledger)


def finish_result(history,period,rows,stream,ledger):
    report=stream.snapshot();signals=[]
    confirmed_points={e['signal_id']:e['point'] for e in ledger.confirmations}
    for rec in ledger.records.values():
        # Once confirmed, display that immutable event's price/anchor. A later
        # decomposition revision withdraws it rather than moving its old marker.
        p=confirmed_points.get(rec['id'],rec['point']);signals.append(dict(id=rec['id'],signal_class=p['class'],label=NAMES[p['class']],side=p['side'],rank=p['rank'],price=p['price'],anchor_index=p['anchor'],anchor_time=rows[p['anchor']]['date'],observed_at=rec['first_seen_at'],confirmed_at=rec.get('confirmed_at'),invalidated_at=rec.get('invalidated_at'),withdrawn_at=rec.get('withdrawn_at'),state=rec['state'],invalidation=p['invalidation'],center_id=p['center_id'],zd=p['zd'],zg=p['zg'],missing=rec['audit']['missing'],evidence=rec['audit'],point=p))
    counts={name:sum(s['signal_class']==name for s in signals) for name in NAMES}
    states={name:sum(s['state']==name for s in signals) for name in ('candidate','confirmed','invalidated','withdrawn')}
    result=dict(ok=True,profile=PROFILE,code=history['code'],name=history.get('name',history['code']),period=period,as_of=rows[-1]['date'],first=rows[0]['date'],bar_count=len(rows),source=history.get('source'),adjustment=history.get('adjustment') or ('qfq' if history.get('adjusted') else 'none'),input_sha256=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest(),bars=rows,signals=signals,events=ledger.events,counts=counts,states=states,
        structure=dict(fractals=stream.fractals,strokes=stream.strokes,segments=stream.segments,centers=[c for l in report['hierarchy']['levels'] for c in l['centers']]),certificate_errors=report['certificate_audit']['errors'],execution_allowed=False,strict_original_equivalence_proven=False,
        definition='包含→分型→笔→特征序列线段→递归中枢→六类结构→逐根事件账本；L0线段边界采用声明口径，只有全部结构门控通过才标为规则确认。',freshness=history.get('history_freshness'))
    if period=='day':result['backtest']=simulate(rows,ledger.events,history['code']);result['candidate_experiment']=simulate(rows,ledger.events,history['code'],'candidate_experiment')
    return result

class ChanService:
    def __init__(self,data_dir):
        self.root=Path(data_dir)/'chan-v1';self.root.mkdir(parents=True,exist_ok=True);self.lock=threading.Lock()
    def result(self,history,period='day',cutoff=None):
        clock=as_of_time(cutoff)
        closure_slot=(clock.date().isoformat(),clock.hour>=15) if cutoff is None else cutoff
        signature=hashlib.sha256(json.dumps([PROFILE,history.get('code'),history.get('adjustment'),history.get('adjusted'),history.get('source'),history.get('native_period'),period,closure_slot,history['bars']],sort_keys=True).encode()).hexdigest();path=self.root/(signature+'.json.gz')
        with self.lock:
            if path.exists():return json.loads(gzip.decompress(path.read_bytes()))
            result=analyze(history,period,cutoff);raw=gzip.compress(json.dumps(result,ensure_ascii=False,separators=(',',':')).encode());path.write_bytes(raw)
            if not cutoff:
                dest=self.root/'results';dest.mkdir(exist_ok=True);(dest/(history['code']+'-'+period+'.json.gz')).write_bytes(raw)
            return result

    def saved(self,code,period):
        if not code.isdigit() or len(code)!=6 or period not in ('day','week','month','1m','5m','15m','30m','60m','quarter','year','5d'):raise ValueError('股票或周期无效')
        path=self.root/'results'/(code+'-'+period+'.json.gz')
        if not path.exists():return None
        result=json.loads(gzip.decompress(path.read_bytes()))
        return result if result.get('profile')==PROFILE else None

    def summary(self):
        path=self.root/'summary.json'
        if not path.exists():return dict(ok=False,message='全市场缠论重算结果尚未就绪')
        value=json.loads(path.read_text(encoding='utf8'))
        if value.get('profile')!=PROFILE:return dict(ok=False,message='旧版本缠论结果已停用，等待当前版本全量复测结果')
        return value
