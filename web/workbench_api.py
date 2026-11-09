"""LiangCe desktop/web contract with an isolated, versioned causal replay engine."""
from collections import OrderedDict
from datetime import datetime,timedelta,timezone
import threading,time
from fastapi import APIRouter,HTTPException
from fastapi.responses import JSONResponse
from web.research_api import symbol
from web.tdx_provider import fetch
from liangce_workbench.chan_live_analysis import LiveAnalysisCache

router=APIRouter(prefix='/api/workbench',tags=['LiangCe workbench'])
CN=timezone(timedelta(hours=8));cache=OrderedDict();guard=threading.Lock();analysis=LiveAnalysisCache()
PERIODS={'day','week','month','1m','5m','15m','30m','60m'}

@router.get('/panel/{code}/{period}')
def panel(code:str,period:str):
    try:code=symbol(code)
    except ValueError as error:raise HTTPException(422,str(error))
    if period not in PERIODS:raise HTTPException(422,'不支持此原生K线周期')
    key=(code,period);now=datetime.now(CN)
    with guard:
        saved=cache.get(key)
        if saved and time.monotonic()-saved[0]<20:result=saved[1]
        else:
            try:bars,meta=fetch(code,period,now)
            except Exception as error:raise HTTPException(503,'实时K线取数失败：'+str(error)[:140])
            if not bars:raise HTTPException(503,'没有真实K线')
            result=dict(symbol=code,period=period,name=code[2:],source_kind='live_market_panel',computed_at=now.isoformat(),fetched_at=now.isoformat(),provenance=meta,
                        bars=[dict(date_cn=datetime.fromisoformat(b.closed_at).astimezone(CN).strftime('%Y-%m-%d %H:%M'),open=b.open,high=b.high,low=b.low,close=b.close,volume=b.volume,is_closed=b.closed)for b in bars])
            cache[key]=(time.monotonic(),result);cache.move_to_end(key)
            while len(cache)>4:cache.popitem(last=False)
    try:state=analysis.get(result)
    except Exception as error:raise HTTPException(503,'缠论结构分析失败：'+str(error)[:140])
    return JSONResponse({**result,'workbench_analysis':state},headers={'Cache-Control':'no-store'})
