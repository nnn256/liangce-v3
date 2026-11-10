"""Liangce research API: evidence-preserving snapshots and bounded compute jobs."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import gzip, hashlib, json, math, os, re, threading, time, uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel, Field, field_validator

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'data/research'
RUNTIME=Path(os.environ.get('LIANGCE_RUNTIME',str(ROOT/'.runtime/research')))
CN=timezone(timedelta(hours=8))
PERIODS={'auction','timeshare','five_days','timeshare_first','day','5d','1m','5m','15m','30m','60m','week','month','quarter','year'}
NATIVE={'day':'1D','5m':'5m','15m':'15m','30m':'30m','60m':'60m','week':'1W','month':'1M'}
router=APIRouter(prefix='/api/research',tags=['量测 v3'])
def bounded_env(name,default,minimum,maximum):
    try:value=int(os.environ.get(name,str(default)))
    except ValueError:value=default
    return max(minimum,min(value,maximum))

WORKERS=bounded_env('LIANGCE_WORKERS',2,1,2)
QUEUE_LIMIT=bounded_env('LIANGCE_QUEUE_LIMIT',4,1,4)
MAX_COMPUTE_BARS=bounded_env('LIANGCE_MAX_COMPUTE_BARS',30000,100,30000)
pool=ThreadPoolExecutor(max_workers=WORKERS,thread_name_prefix='liangce')
lock=threading.RLock();jobs:dict[str,dict]={}


def symbol(value):
    raw=value.strip().lower()
    if re.fullmatch(r'\d{6}\.(sh|sz|bj)',raw):code,exchange=raw.split('.');raw=exchange+code
    if re.fullmatch(r'\d{6}',raw):raw=('bj' if raw.startswith(('4','8','92')) else 'sh' if raw.startswith('6') else 'sz')+raw
    if not re.fullmatch(r'(sh6\d{5}|sz(?:0|30)\d{4,5}|bj\d{6})',raw) or len(raw)!=8:raise ValueError('请输入有效的沪深京A股六位代码')
    return raw


def validate_period(value):
    if value not in PERIODS:raise ValueError('不支持的周期')
    return value


@lru_cache(maxsize=1)
def manifest():return json.loads((ARCHIVE/'manifest.json').read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def read_snapshot(code,period):
    path=ARCHIVE/f'{code}__{period}.json.gz'
    if not path.is_file():raise HTTPException(404,'该股票/周期没有已归档研究，请连接后端并重新计算')
    compressed=path.read_bytes();entry=next((x for x in manifest()['files'] if x['file']==path.name),None)
    if entry and hashlib.sha256(compressed).hexdigest()!=entry['sha256']:raise HTTPException(500,'研究归档校验失败')
    panel=json.loads(gzip.decompress(compressed))
    if panel.get('kind')=='candles':
        from chanmodel.model import Candle
        from chanmodel.stroke_signals import snapshot
        bars=[Candle(i,*[row[key] for key in ['open','high','low','close']],row['date_cn'].replace(' ','T')+':00+08:00',row['volume'],row.get('is_closed',True)) for i,row in enumerate(panel['bars']) if row.get('is_closed',True)]
        if len(bars)>=3:panel['stroke_model']=snapshot(bars)
    return panel


def check_write(request):
    expected=os.environ.get('LIANGCE_API_TOKEN')
    if expected and request.headers.get('authorization')!='Bearer '+expected:raise HTTPException(401,'计算接口需要服务器访问令牌')
    origin=request.headers.get('origin')
    allowed={x.strip().rstrip('/') for x in os.environ.get('LIANGCE_ALLOWED_ORIGINS','').split(',') if x.strip()}
    if origin and origin.rstrip('/') not in allowed and origin.rstrip('/')!=str(request.base_url).rstrip('/'):
        raise HTTPException(403,'此来源未获准提交计算任务')
    if os.environ.get('LIANGCE_READONLY')=='1':raise HTTPException(403,'当前公开服务只读，计算请连接个人后端')


@router.get('/health')
def health():
    return {'status':'ok','product':'量测 v3','version':'3.0.0','snapshot_date':manifest()['as_of'],
            'source':'verified_historical_snapshot','compute_enabled':os.environ.get('LIANGCE_READONLY')!='1',
            'authentication_required':bool(os.environ.get('LIANGCE_API_TOKEN')),'running_jobs':sum(j['state']=='running' for j in jobs.values()),
            'hosting':os.environ.get('LIANGCE_HOSTING','local'),
            'compute_limits':{'workers':WORKERS,'queue':QUEUE_LIMIT,'max_input_bars':MAX_COMPUTE_BARS},
            'runtime_storage':'ephemeral' if os.environ.get('LIANGCE_EPHEMERAL')=='1' else 'local',
            'live_chart_enabled':True,'live_chart_periods':['auction','timeshare','five_days','1m','5m','15m','30m','60m','day','5d','week','month','quarter','year'],
            'auction_quote_enabled':True,'monitor_signal_enabled':True,'monitor_delivery_scope':'open browser page; browser notification permission required; no guaranteed delivery after close',
            'unsupported_signal_views':{'auction':'竞价价格快照缺少连续OHLC与次级走势证据，不生成六类确认点'},
            'live_chart_source':('oficcejo/tdx-api@ea07dccb67aeb92ebde851ac31503b4bf457a318'
                                 if os.environ.get('LIANGCE_TDX_API') or os.environ.get('LIANGCE_TDX_BINARY') else
                                 'acb6104/opentdx' if os.environ.get('LIANGCE_OPENTDX_PYTHON') else 'stock-dashboard/market_gateway'),
            'tdx_configured':bool(os.environ.get('LIANGCE_TDX_API') or os.environ.get('LIANGCE_TDX_BINARY') or os.environ.get('LIANGCE_OPENTDX_PYTHON')),
            'refresh_seconds':{'quotes_trading':10,'chart_trading':15,'outside_trading_hours':300},
            'frontend_url':'https://nnn256.github.io/liangce-v3/',
            'engine':'original_clause_gated_causal_confirmation_v1','execution_allowed':False}


@router.get('/catalog')
def catalog():return manifest()


@lru_cache(maxsize=1)
def local_symbols():
    verified=ARCHIVE/'symbols.json'
    if verified.exists():return json.loads(verified.read_text(encoding='utf-8'))
    data=json.loads((ROOT/'data/stock_names.json').read_text(encoding='utf-8'))
    result=[]
    pairs=data.items() if isinstance(data,dict) else [(str(x.get('code','')),x.get('name','')) for x in data]
    for code,name in pairs:
        try:s=symbol(code)
        except ValueError:continue
        result.append({'symbol':s,'code':s[2:],'name':str(name),'market':s[:2].upper(),'archived':s=='sz300949'})
    if not any(x['symbol']=='sz300949' for x in result):result.append({'symbol':'sz300949','code':'300949','name':'奥雅股份','market':'SZ','archived':True})
    return result


@router.get('/symbols')
def search(q:str='',limit:int=20):
    q=q.strip().lower()[:40];limit=max(1,min(limit,50))
    result=[x for x in local_symbols() if q in x['code'] or q in x['name'].lower() or q in x['symbol']]
    result.sort(key=lambda x:(not x['archived'],x['symbol']))
    return {'results':result[:limit],'total':len(result),'source':'repository_stock_dictionary'}


@router.get('/panel/{code}/{period}')
def panel(code:str,period:str,request:Request):
    try:code=symbol(code);validate_period(period)
    except ValueError as e:raise HTTPException(422,str(e))
    key=f'{code}__{period}';path=RUNTIME/'latest'/f'{key}.json.gz'
    if path.is_file():body=gzip.decompress(path.read_bytes())
    else:body=json.dumps(read_snapshot(code,period),ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
    etag='"'+hashlib.sha256(body).hexdigest()+'"'
    if request.headers.get('if-none-match')==etag:return Response(status_code=304,headers={'ETag':etag})
    return Response(body,media_type='application/json',headers={'ETag':etag,'Cache-Control':'no-cache','X-Data-Source':'research-evidence'})


@router.get('/quote/{code}')
def quote(code:str):
    try:code=symbol(code)
    except ValueError as e:raise HTTPException(422,str(e))
    import market_gateway as mg
    market_symbol=code[2:]+'.'+code[:2].upper()
    data=mg.fetch_level1_quotes([market_symbol]).get(market_symbol)
    if not data:raise HTTPException(503,'行情源暂不可用；已有研究快照不受影响')
    return {'quote':data,'source':'stock-dashboard/market_gateway','received_at':datetime.now(CN).isoformat(),
            'meaning':'行情报价与研究快照分别显示；刷新报价不改变历史确认'}


@router.get('/live-panel/{code}/{period}')
def realtime_panel(code:str,period:str,refresh:bool=False):
    try:code=symbol(code);validate_period(period)
    except ValueError as error:raise HTTPException(422,str(error))
    from web.realtime_panel import live_panel
    return JSONResponse(live_panel(code,period,refresh=refresh),headers={'Cache-Control':'no-store'})


@router.get('/period-signals/{code}')
def signal_periods(code:str):
    try:code=symbol(code)
    except ValueError as error:raise HTTPException(422,str(error))
    from web.realtime_panel import period_overview
    return JSONResponse(period_overview(code),headers={'Cache-Control':'no-store'})


@router.get('/monitor-signals/{code}/{period}')
def monitor_signals(code:str,period:str,resolution:str='stroke'):
    try:code=symbol(code)
    except ValueError as error:raise HTTPException(422,str(error))
    if resolution not in {'stroke','segment'} or period not in {'1m','5m','15m','30m','60m','day','5d','week','month','quarter','year'}:
        raise HTTPException(422,'信号监控请选择笔级/线段及K线周期')
    from web.realtime_panel import live_panel
    panel=live_panel(code,period);model=panel['stroke_model'] if resolution=='stroke' else panel
    confirmed={item['signal_id']:item for item in model.get('confirmations',[])}
    records={item['id']:item for item in model.get('confirmation_records',[])}
    points=[]
    for point in model.get('signals',[]):
        record=records.get(point['id'],{})
        points.append({'id':point['id'],'class':point['class'],'side':point['side'],'rank':point.get('rank',0),
            'price':point['price'],'anchor_time':point['event_time'],'available_time':point.get('available_time'),
            'state':record.get('state',point['state']),'confirmed':point['id'] in confirmed,
            'confirmation_origin':record.get('confirmation_origin'),'evidence_at':record.get('evidence_at'),
            'confirmed_at':confirmed.get(point['id'],{}).get('confirmed_at'),'definition_mode':point.get('definition_mode'),
            'confirmation_semantics':confirmed.get(point['id'],{}).get('confirmation_semantics')})
    return JSONResponse({'symbol':code,'period':period,'resolution':resolution,'signals':points,'fetched_at':panel['fetched_at'],
        'structure_as_of':panel['structure_as_of'],'source':panel['provenance']['source'],'market_session':panel['market_session'],
        'definition_mode':'stroke_proxy' if resolution=='stroke' else panel['definition_mode'],
        'observation_scope':'current_live_evidence; first subscription establishes baseline without historical notifications',
        'refresh_after_seconds':30 if panel['market_session']=='trading_hours' else 300,'execution_allowed':False},headers={'Cache-Control':'no-store'})


@router.post('/precision-backtests')
def precision_backtests(payload:dict,request:Request):
    check_write(request)
    try:code=symbol(payload.get('symbol',''));resolution=payload.get('resolution','segment');periods=payload.get('periods')
    except (ValueError,TypeError) as error:raise HTTPException(422,str(error))
    from web.precision_backtest import start
    return JSONResponse(start(code,resolution,periods),status_code=202,headers={'Cache-Control':'no-store'})


@router.get('/precision-backtests/{ident}')
def precision_status(ident:str):
    from web.precision_backtest import status
    return JSONResponse(status(ident),headers={'Cache-Control':'no-store'})


@router.get('/saved-replays/{code}/{resolution}')
def saved_replay(code:str,resolution:str):
    try:code=symbol(code)
    except ValueError as error:raise HTTPException(422,str(error))
    from web.precision_backtest import available
    return JSONResponse(available(code,resolution),headers={'Cache-Control':'no-store'})


@router.get('/precision-backtests/{ident}/{period}')
def precision_detail(ident:str,period:str):
    from web.precision_backtest import detail
    return JSONResponse(detail(ident,period),headers={'Cache-Control':'no-store'})


quote_cache=OrderedDict()
quote_lock=threading.Lock()


def quote_session(now):
    minute=now.hour*60+now.minute
    return now.weekday()<5 and (555<=minute<=690 or 780<=minute<=900)


def normalized_quote(code,data,received_at):
    def number(key):
        try:value=float(data[key])
        except (KeyError,ValueError,TypeError):return None
        return value if math.isfinite(value) else None
    price=number('price');previous=number('prevClose')
    if price is None or price<=0:return None
    change=round(price-previous,3) if previous and previous>0 else None
    pct=number('changePercent') if change is not None else None
    if pct is None and change is not None:pct=round(change/previous*100,4)
    stamp=data.get('quoteTime');market_time=None
    if stamp:
        try:
            text=str(stamp)
            parsed=datetime.strptime(text,'%Y%m%d%H%M%S') if re.fullmatch(r'\d{14}',text) else datetime.fromisoformat(text)
            market_time=parsed.replace(tzinfo=CN).isoformat() if parsed.tzinfo is None else parsed.astimezone(CN).isoformat()
        except ValueError:pass
    return {'symbol':code,'name':data.get('name') or code,'price':price,'previous_close':previous,
            'change':change,'change_percent':pct,'market_time':market_time,'received_at':received_at,
            'source':'stock-dashboard/market_gateway','stale':False}


@router.get('/quotes')
def quotes(symbols:str):
    parts=symbols.split(',')
    if not 1<=len(parts)<=80 or len(symbols)>1200:raise HTTPException(422,'每次最多查询80只股票')
    try:codes=list(dict.fromkeys(symbol(x) for x in parts))
    except ValueError as error:raise HTTPException(422,str(error))
    now=datetime.now(CN);active=quote_session(now);ttl=5 if active else 300
    failure=None
    # Serialize cache misses so concurrent visitors share one upstream batch.
    with quote_lock:
        missing=[code for code in codes if code not in quote_cache or time.monotonic()-quote_cache[code][0]>=ttl]
        if missing:
            import market_gateway as mg
            try:raw=mg.fetch_level1_quotes([code[2:]+'.'+code[:2].upper() for code in missing])
            except Exception:raw={}
            received=datetime.now(CN).isoformat()
            for code in missing:
                data=raw.get(code[2:]+'.'+code[:2].upper())
                item=normalized_quote(code,data,received) if data else None
                if item:
                    quote_cache[code]=(time.monotonic(),item);quote_cache.move_to_end(code)
            while len(quote_cache)>500:quote_cache.popitem(last=False)
            if any(code not in quote_cache or time.monotonic()-quote_cache[code][0]>=ttl for code in missing):
                failure='部分行情源暂不可用；已有报价保留并标记为上次数据'
        results={code:{**quote_cache[code][1],'stale':time.monotonic()-quote_cache[code][0]>=ttl} for code in codes if code in quote_cache}
    if not results:raise HTTPException(503,'行情源暂不可用，请稍后重试；未使用演示报价')
    return {'quotes':results,'missing':[code for code in codes if code not in results],
            'market_session':'trading_hours' if active else 'outside_trading_hours',
            'refresh_after_seconds':10 if active else 300,'error':failure,
            'received_at':datetime.now(CN).isoformat(),'meaning':'休市保留最近交易报价；报价时间与结构快照时间分别记录'}


class JobRequest(BaseModel):
    symbol:str='sz300949'
    period:str='day'
    source:Literal['archive','live']='archive'
    mode:Literal['analysis','backtest']='analysis'
    cutoff:str|None=None
    @field_validator('symbol')
    @classmethod
    def stock(cls,v):return symbol(v)
    @field_validator('period')
    @classmethod
    def period_name(cls,v):return validate_period(v)
    @field_validator('cutoff')
    @classmethod
    def cutoff_date(cls,v):
        if v:
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',v):raise ValueError('截止日期格式为YYYY-MM-DD')
            datetime.strptime(v,'%Y-%m-%d')
        return v


def live_bars(code,period):
    from chanmodel.model import Candle
    from web import tdx_provider
    if tdx_provider.enabled():
        bars,metadata=tdx_provider.fetch(code,period,datetime.now(CN))
        return bars,{**metadata,'confirmation_eligible':metadata.get('split_adjustment_verified') is True}
    if period not in NATIVE:raise ValueError('此周期暂只支持已归档数据；上游原生接口不提供该周期，不能用其他周期替代')
    import market_gateway as mg
    result=mg.fetch_symbol_klines(code[2:]+'.'+code[:2].upper(),NATIVE[period]);items=result.get('klines',[])
    if len(items)<3:raise ValueError('上游未返回足够的真实K线')
    from web.realtime_panel import provider_bars
    out=provider_bars(items,period,datetime.now(CN))
    # The legacy gateway doesn't certify adjustment consistently across sources.
    # Keep its source quality visible and never publish confirmed original-rule signals.
    return out,{'source':'stock-dashboard/market_gateway','adjustment':'provider_unspecified','volume_unit':'upstream_hands_converted_to_shares',
                'confirmation_eligible':False,'quality_note':'上游复权/原生完整性未认证，本次只生成结构候选'}


def build_dynamic(req,ident):
    from chanmodel.model import Candle,time_value
    from chanmodel.complete_study import analyze_complete
    from chanmodel.causal_replay import StreamingStructure,SignalLedger,abcd_objects
    try:
        with lock:jobs[ident].update(state='running',progress=5)
        if req.source=='archive':
            original=read_snapshot(req.symbol,req.period)
            if original['kind']=='line':raise ValueError('分时价格快照不包含OHLC，不能用于结构确认回测')
            raw=original['bars'];bars=[Candle(i,b['open'],b['high'],b['low'],b['close'],b['date_cn'].replace(' ','T')+':00+08:00',b['volume'],b.get('is_closed',True)) for i,b in enumerate(raw)]
            provenance={'source':'verified_historical_snapshot','adjustment':original.get('adjustment_note'),'confirmation_eligible':True}
            name=original['name']
        else:
            bars,provenance=live_bars(req.symbol,req.period);original={};name=next((x['name'] for x in local_symbols() if x['symbol']==req.symbol),req.symbol)
        cutoff=(req.cutoff+'T23:59:59+08:00') if req.cutoff else datetime.now(CN).isoformat()
        bars=[b for b in bars if b.closed and time_value(b.closed_at)<=time_value(cutoff)]
        if len(bars)<3:raise ValueError('截止日期内少于3根闭合K线')
        if len(bars)>MAX_COMPUTE_BARS:raise ValueError(f'当前实例单次最多计算{MAX_COMPUTE_BARS:,}根K线，本次有{len(bars):,}根。请指定更早截止日期缩短回放，全部历史图和基准回测仍可直接查看。')
        digest=hashlib.sha256(json.dumps([[b.closed_at,b.open,b.high,b.low,b.close,b.volume] for b in bars]).encode()).hexdigest()
        with lock:jobs[ident]['progress']=15
        report=analyze_complete(req.symbol,req.period,bars,cutoff,digest);ledger=None
        if req.mode=='backtest':
            if not provenance['confirmation_eligible']:raise ValueError('上游数据口径未认证，不能用于已确认信号回测')
            stream=StreamingStructure();ledger=SignalLedger(req.period)
            for i,b in enumerate(bars):
                changed=stream.append(b);ledger.invalidate(b)
                if changed:ledger.observe(stream.snapshot(),b,stream.bars)
                if i%500==0:
                    with lock:jobs[ident]['progress']=15+int(75*(i+1)/len(bars))
        points=[{'time':int(datetime.fromisoformat(b.closed_at).timestamp())+8*3600,'source_index':b.pos,'date_cn':b.closed_at[:16].replace('T',' '),
                 'open':b.open,'high':b.high,'low':b.low,'close':b.close,'volume':b.volume,'is_closed':b.closed} for b in bars]
        result={'schema':'liangce.research.v1','symbol':req.symbol,'name':name,'period':req.period,'label':original.get('label',req.period),'kind':'candles','bars':points,
                'coverage':{'count':len(points),'first':points[0]['date_cn'],'last':points[-1]['date_cn'],'input_sha256':digest,'source':provenance['source'],'forming_count':0},
                **{k:report[k] for k in ['profile','definition_mode','approximation_loss','decompositions','divergence_comparisons','center_evolution']},
                **{k:report['base'][k] for k in ['fractals','merged','strokes','segments']},
                'all_centers':[c for layer in report['hierarchy']['levels'] for c in layer['centers']],
                'signals':report['signals'],'divergences':report['divergence_comparisons'],'monitors':report['center_monitors'],'features':report['feature_sequences'],
                'abcd':abcd_objects(report),'macd':[dict(time=points[i]['time'],**h) for i,h in enumerate(report['macd'])],
                'confirmations':ledger.confirmations if ledger else [],'signal_events':ledger.events if ledger else [],'portfolio_metrics':None,'portfolio_trades':[],'portfolio_equity':[],
                'source_kind':provenance['source'],'provenance':provenance,'data_as_of':bars[-1].closed_at,'computed_at':datetime.now(CN).isoformat(),
                'raw_last_price':original.get('raw_last_price') if not req.cutoff else None,'analysis_last_price':bars[-1].close,
                'adjustment_note':provenance['adjustment'],'execution_allowed':False,'strict_original_equivalence_proven':False,
                'backtest_scope_note':'本次重放返回候选/确认/失效账本；成交收益查看已核验基准回测。' if ledger else '结构快照，未逐根重跑确认链'}
        if req.source=='archive' and req.symbol=='sz300949':
            actions=json.loads((ARCHIVE/'corporate-actions.json').read_text(encoding='utf-8'))['actions'];factor=1.
            for action in actions:
                if bars[-1].closed_at[:10]>=action['ex_date']:factor*=action['share_multiplier']
            result['raw_last_price']=bars[-1].close/factor
        result['signal_counts']={k:sum(p['class']==k for p in report['signals']) for k in ['first_buy','second_buy','third_buy','first_sell','second_sell','third_sell']}
        compressed=gzip.compress(json.dumps(result,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode(),mtime=0)
        folder=RUNTIME/'jobs'/ident;folder.mkdir(parents=True,exist_ok=True);(folder/'panel.json.gz').write_bytes(compressed)
        # Dated replays never replace the latest snapshot.
        if not req.cutoff:
            latest=RUNTIME/'latest';latest.mkdir(parents=True,exist_ok=True);tmp=latest/f'{req.symbol}__{req.period}.tmp';tmp.write_bytes(compressed);tmp.replace(latest/f'{req.symbol}__{req.period}.json.gz')
        with lock:jobs[ident].update(state='completed',progress=100,result_url=f'/api/research/jobs/{ident}/result',finished_at=datetime.now(CN).isoformat())
    except Exception as exc:
        with lock:jobs[ident].update(state='failed',error=str(exc)[:500],finished_at=datetime.now(CN).isoformat())


@router.post('/jobs',status_code=202)
def create(req:JobRequest,request:Request):
    check_write(request)
    with lock:
        active=[j for j in jobs.values() if j['state'] in {'queued','running'}]
        same=next((j for j in active if j['request']==req.model_dump()),None)
        if same:return same
        if len(active)>=QUEUE_LIMIT:raise HTTPException(429,'当前计算队列已满，请等待现有任务完成')
        if len(jobs)>=100:
            done=[k for k,v in jobs.items() if v['state'] not in {'queued','running'}]
            for k in done[:20]:jobs.pop(k,None)
        ident=uuid.uuid4().hex;job={'id':ident,'state':'queued','progress':0,'request':req.model_dump(),'created_at':datetime.now(CN).isoformat()};jobs[ident]=job
    pool.submit(build_dynamic,req,ident);return job


@router.get('/jobs/{ident}')
def job(ident:str):
    with lock:
        if ident not in jobs:raise HTTPException(404,'任务不存在或服务已重启')
        return dict(jobs[ident])


@router.get('/jobs/{ident}/result')
def job_result(ident:str):
    if not re.fullmatch(r'[0-9a-f]{32}',ident):raise HTTPException(422,'无效任务编号')
    p=RUNTIME/'jobs'/ident/'panel.json.gz'
    if not p.is_file():raise HTTPException(404,'任务结果尚未生成')
    return Response(gzip.decompress(p.read_bytes()),media_type='application/json')
