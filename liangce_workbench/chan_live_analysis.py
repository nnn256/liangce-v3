"""Bounded live replay sessions using the exact workstation engine and ledger."""
import copy
import hashlib
import json
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from .chan_service import PROFILE,bar_time,finish_result
from .chanmodel.model import Candle
from .chanmodel.causal_replay import StreamingStructure,SignalLedger,CONFIG
from .chanmodel.structure import merge_bars,fractals_at,strokes_at


def history_from_panel(panel):
    period=panel['period'];rows=[]
    for b in panel['bars']:
        if b.get('is_closed') is not True:continue
        rows.append(dict(date=b['date_cn'][:16] if period.endswith('m') else b['date_cn'][:10],
                         **{k:b[k] for k in ('open','high','low','close','volume')},is_closed=True))
    if not rows:raise ValueError('没有已闭合K线，暂不计算结构')
    return dict(code=panel['symbol'][2:],name=panel.get('name',panel['symbol']),native_period=period,
                source=panel['provenance']['source'],adjustment=panel['provenance']['adjustment'],bars=rows)


def candles(rows):
    return [Candle(i,b['open'],b['high'],b['low'],b['close'],bar_time(b['date']).isoformat(),b['volume'],True) for i,b in enumerate(rows)]


def fingerprint(history):
    return hashlib.sha256(json.dumps([PROFILE,history['code'],history['native_period'],history['adjustment'],history['bars']],sort_keys=True,separators=(',',':')).encode()).hexdigest()


def geometry(history):
    bars=candles(history['bars']);merged=merge_bars(bars,CONFIG);fractals=fractals_at(merged);strokes,_=strokes_at(fractals,CONFIG)
    return dict(ok=True,profile=PROFILE,code=history['code'],name=history['name'],period=history['native_period'],
                bars=history['bars'],first=history['bars'][0]['date'],as_of=history['bars'][-1]['date'],bar_count=len(bars),
                adjustment=history['adjustment'],source=history['source'],signals=[],counts={},states={},
                structure=dict(fractals=fractals,strokes=strokes,segments=[],centers=[]),replay_pending=True,
                definition='包含处理后的顶底分型与笔已计算；六类点逐根回放中。',execution_allowed=False)


class ReplaySession:
    def __init__(self,history):
        self.history=history;self.rows=[];self.stream=StreamingStructure();self.ledger=SignalLedger(history['native_period'])
    def extend(self,history,progress=lambda _:None):
        new=history['bars']
        same_basis=(self.history['adjustment']==history['adjustment'] and self.history['native_period']==history['native_period'] and self.history['code']==history['code'])
        if not same_basis or new[:len(self.rows)]!=self.rows:
            self.rows=[];self.stream=StreamingStructure();self.ledger=SignalLedger(history['native_period'])
        for i in range(len(self.rows),len(new)):
            b=new[i];bar=Candle(i,b['open'],b['high'],b['low'],b['close'],bar_time(b['date']).isoformat(),b['volume'],True)
            changed=self.stream.append(bar);self.ledger.invalidate(bar)
            if changed:self.ledger.observe(self.stream.snapshot(),bar,self.stream.bars)
            self.rows.append(copy.deepcopy(b))
            if i%100==0:progress(i+1)
        self.history=history;progress(len(new))
        return copy.deepcopy(finish_result(history,history['native_period'],self.rows,self.stream,self.ledger))


class LiveAnalysisCache:
    def __init__(self,max_sessions=2):
        self.lock=threading.RLock();self.entries=OrderedDict();self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='workbench-replay');self.max_sessions=max_sessions
    def get(self,panel):
        history=history_from_panel(panel);key=(history['code'],history['native_period']);digest=fingerprint(history)
        with self.lock:
            entry=self.entries.get(key)
            if entry and entry['digest']==digest:
                self.entries.move_to_end(key);return self.view(entry)
            if entry and entry['status']=='running':
                return dict(status='updating',profile=PROFILE,completed=entry['completed'],total=len(history['bars']),message='已有回放正在处理，完成后同步新增K线')
            if sum(e['status']=='running' for e in self.entries.values())>=self.max_sessions:
                return dict(status='queued',profile=PROFILE,completed=0,total=len(history['bars']),message='回放队列正在处理其他周期')
            session=entry['session'] if entry else ReplaySession(history)
            entry=dict(digest=digest,session=session,status='running',completed=0,total=len(history['bars']),preview=geometry(history),result=None,error=None)
            self.entries[key]=entry;self.entries.move_to_end(key)
            self.pool.submit(self.run,key,entry,history)
            while len(self.entries)>self.max_sessions:
                removable=next((k for k,e in self.entries.items() if e['status']!='running' and k!=key),None)
                if removable is None:break
                del self.entries[removable]
            return self.view(entry)
    def run(self,key,entry,history):
        try:
            result=entry['session'].extend(history,lambda count:entry.update(completed=count))
            with self.lock:entry.update(result=result,status='ready',preview=None)
        except Exception as error:
            with self.lock:entry.update(status='failed',error=str(error))
    def view(self,entry):
        return dict(status=entry['status'],profile=PROFILE,input_sha256=entry['digest'],completed=entry['completed'],total=entry['total'],
                    result=entry['result'] if entry['status']=='ready' else entry['preview'],message=entry['error'])
    def close(self):self.pool.shutdown(wait=False,cancel_futures=True)
