"""Transient structural changes driven by the unfinished candle.

This view never enters the closed-bar signal ledger or historical backtests.
"""
from dataclasses import replace
import copy,hashlib,json


FIELDS=('start','end','source','anchor','price','start_price','end_price','zd','zg','low','high','state','basis_at','available_at')


def changes(items,stable,now):
    prior={item['id']:item for item in stable};result=[]
    for item in items:
        old=prior.get(item['id'])
        if old and all(item.get(field)==old.get(field) for field in FIELDS):continue
        preview=copy.deepcopy(item)
        preview['preview_status']=item.get('state')
        preview.update(state='live_preview',live_preview=True,has_confirmation=False,confirmed_at=None,
                       preview_at=now.isoformat(),execution_allowed=False,
                       confirmation_origin='unfinished_candle_preview',preview_replaces_id=item['id'])
        if 'rule_audit' in preview:preview['rule_audit']={**preview['rule_audit'],'passed':False,'preview_only':True}
        result.append(preview)
    return result


def preview_models(code,period,candles,now,report,fine,build):
    if not any(not bar.closed for bar in candles):return None
    # Promote only inside an isolated hypothetical view. Source bars and the
    # confirmed model retain their real closed=False flags and timestamps.
    assumed=[replace(bar,closed=True) for bar in candles]
    digest=hashlib.sha256(json.dumps([[bar.closed_at,bar.open,bar.high,bar.low,bar.close,bar.volume] for bar in assumed]).encode()).hexdigest()
    tentative,small=build(code,period,assumed,assumed[-1].closed_at,digest)
    stable_centers=[c for layer in report['hierarchy']['levels'] for c in layer['centers']]
    tentative_centers=[c for layer in tentative['hierarchy']['levels'] for c in layer['centers']]
    def tail(units,resolution):
        if not units:return []
        unit=units[-1];anchor=unit['start'] if unit['state']!='confirmed' else unit['end']
        start=unit['start_price'] if unit['state']!='confirmed' else unit['end_price'];last=candles[-1]
        if anchor>=last.pos:return []
        return [{'id':'tail:'+resolution+':'+str(anchor),'start':anchor,'end':last.pos,'start_price':start,
                 'end_price':last.close,'price':last.close,'direction':'up' if last.close>=start else 'down',
                 'resolution':resolution,'state':'live_preview','live_preview':True,'preview_at':now.isoformat(),
                 'type':'末端价格走势预览','execution_allowed':False,
                 'preview_note':'从最近结构边界连至当前未收盘价格，仅作动态观察；不表示已满足成笔或成段条件'}]
    return {'observed_at':now.isoformat(),'definition_mode':'unfinished_candle_preview',
            'not_confirmed':True,'execution_allowed':False,'input_sha256':digest,
            'note':'包含未收盘K线的动态预览，可变化或消失；不参与规则确认、交易回测或确认提醒',
            'tails':{'stroke':tail(fine['strokes'],'stroke'),'segment':tail(report['base']['segments'],'segment')},
            'stroke':{key:changes(small.get(key,[]),fine.get(key,[]),now) for key in ['fractals','strokes','centers','signals']},
            'segment':{'fractals':changes(tentative['base']['fractals'],report['base']['fractals'],now),
                       'strokes':changes(tentative['base']['strokes'],report['base']['strokes'],now),
                       'segments':changes(tentative['base']['segments'],report['base']['segments'],now),
                       'centers':changes(tentative_centers,stable_centers,now),
                       'signals':changes(tentative['signals'],report['signals'],now)}}
