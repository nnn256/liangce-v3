"""All-period prefix replay and real costed fills for the selected symbol.

Stroke observations and recursive original-clause gates are separate models.
Neither model may trade on the earlier price anchor or an unfinished candle.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import bisect,copy,gzip,hashlib,json,os,threading,time,uuid

from fastapi import HTTPException
from chanmodel.model import Candle,Config
from chanmodel.stroke_signals import replay as stroke_replay,CLASSES
from chanmodel.causal_replay import StreamingStructure,SignalLedger
from chanmodel.causal_portfolio import simulate,CostModel
from web import tdx_provider as tdx

ROOT=Path(__file__).resolve().parents[1]
PERIODS=['1m','5m','15m','30m','60m','day','5d','week','month','quarter','year']
pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='precision-replay')
lock=threading.RLock();runs={}


def runtime():return Path(os.environ.get('LIANGCE_RUNTIME',str(ROOT/'.runtime/research')))/'precision'
ARCHIVE=ROOT/'data/precision-replays'


def pack(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode(),mtime=0)
    temporary=path.with_suffix('.tmp');temporary.write_bytes(raw);temporary.replace(path)


def chart_context(code,period,bars,digest):
    from chanmodel.complete_study import analyze_complete
    from chanmodel.causal_replay import abcd_objects
    from chanmodel.signals import macd
    report=analyze_complete(code,period,bars,bars[-1].closed_at,digest)
    return {**{key:report['base'][key] for key in ['strokes','segments','fractals']},
            'macd':[dict(time=int(datetime.fromisoformat(bar.closed_at).timestamp())+8*3600,**value)
                    for bar,value in zip(bars,macd(bars,Config(macd_multiplier=2)))],
            'all_centers':[c for level in report['hierarchy']['levels'] for c in level['centers']],
            'abcd':abcd_objects(report)}


def records_from_ledger(ledger):
    return [{**{key:value for key,value in rec.items() if key!='point'},'current_state':rec['state']} for rec in ledger.records.values()]


def definition_fields(period,resolution):
    from chanmodel.stroke_signals import APPROXIMATION_LOSS
    return {'timeframe':period,'trade_level':'stroke_observation' if resolution=='stroke' else 'recursive_rank_per_signal',
            'confirm_level':'completed_stroke_on_closed_kline' if resolution=='stroke' else 'declared_recursive_clause_gates',
            'trigger_level':'same_timeframe_no_lower_movement_verification' if resolution=='stroke' else 'declared_lower_movement_per_signal',
            'structure_completeness':'inclusion_fractal_stroke_overlap_proxy' if resolution=='stroke' else 'declared_recursive_profile_not_all_original_equivalence',
            'approximation_loss':APPROXIMATION_LOSS if resolution=='stroke' else '底层线段、力度和完成分解使用声明规范；未证明原文全部解释等价'}


def raw_from_adjusted(code,bars,metadata):
    actions=metadata.get('corporate_actions',[]);result=[]
    for i,bar in enumerate(bars):
        factor=1.
        for action in actions:
            if bar.closed_at[:10]>=action['ex_date']:factor*=action['share_multiplier']
        result.append(Candle(i,*[round(value/factor,8) for value in [bar.open,bar.high,bar.low,bar.close]],bar.closed_at,bar.volume,True))
    return result


def prefix_events(bars,period,resolution,progress=None):
    if resolution=='stroke':return stroke_replay(bars,period,progress=progress)
    stream=StreamingStructure();ledger=SignalLedger(period)
    for i,bar in enumerate(bars):
        changed=stream.append(bar);ledger.invalidate(bar)
        if changed:ledger.observe(stream.snapshot(),bar,stream.bars)
        if progress and (i%500==0 or i==len(bars)-1):progress(i+1,len(bars))
    final=stream.snapshot()
    return {'profile':'original_clause_gated_causal_confirmation_v1','definition_mode':'declared_recursive_profile',
            'signals':[rec['point'] for rec in ledger.records.values()],'confirmations':ledger.confirmations,
            'signal_events':ledger.events,'confirmation_records':records_from_ledger(ledger),
            **{key:final['base'][key] for key in ['strokes','segments','fractals']},
            'all_centers':[center for layer in final['hierarchy']['levels'] for center in layer['centers']]}


def portfolio(code,period,bars,events,metadata,daily_bars,daily_meta):
    daily_raw=raw_from_adjusted(code,daily_bars,daily_meta)
    closes={b.closed_at[:10]:b.close for b in daily_raw}
    actions=daily_meta.get('corporate_actions',[])
    price_limit=.20 if code.startswith(('sz30','sh688')) else .30 if code.startswith('bj') else .10
    cost=CostModel(price_limit=price_limit)
    if period in {'day','1m','5m','15m','30m','60m'}:
        raw=raw_from_adjusted(code,bars,metadata)
        return simulate(raw,bars,events,closes,actions,cost,period)
    # Calendar-period decisions execute on the next DAILY opening, not a
    # fictional week/month opening inferred by subtracting minutes.
    stamps=[b.closed_at for b in daily_bars];mapped=[]
    for event in events:
        index=bisect.bisect_right(stamps,event['observed_at'])-1
        if index<0:continue
        mapped.append({**event,'source_period_index':event['observed_index'],'observed_index':index})
    result=simulate(daily_raw,daily_bars,mapped,closes,actions,cost,'day')
    result['calendar_execution']='signals observed at period close, executed on next available daily open'
    return result


def execute_period(code,period,resolution,bars,metadata,daily_bars,daily_meta,progress=None):
    closed=[bar for bar in bars if bar.closed]
    if not closed:raise ValueError('没有闭合K线')
    insufficient=len(closed)<3
    replay=({'profile':'insufficient_closed_history','definition_mode':'insufficient_data','signals':[],'confirmations':[],
             'signal_events':[],'confirmation_records':[]} if insufficient else prefix_events(closed,period,resolution,progress))
    if progress:progress(len(closed),len(closed))
    eligible=metadata.get('split_adjustment_verified') is True
    # Rule confirmation remains available for a reproducible study; data
    # certification and original equivalence remain separate evidence fields.
    replay['original_data_certified']=eligible
    fills=portfolio(code,period,closed,replay['signal_events'],metadata,daily_bars,daily_meta)
    class_stats={}
    for kind in CLASSES:
        confirms=[e for e in replay['confirmations'] if e['class']==kind]
        recs=[r for r in replay['confirmation_records'] if next((p for p in replay['signals'] if p['id']==r['id'] and p['class']==kind),None)]
        class_stats[kind]={'observed':len(recs),'rule_confirmed':len(confirms),
                           'invalidated':sum(r['state']=='invalidated' for r in recs),
                           'withdrawn':sum(r['state']=='withdrawn' for r in recs),
                           'median_delay_bars':sorted(e['observed_index']-e['anchor'] for e in confirms)[len(confirms)//2] if confirms else None}
    for event in replay['confirmations']:
        if not 0<=event['anchor']<=event['observed_index']<len(closed):raise ValueError('回放信号引用未来或越界K线')
    for order in fills['orders']:
        # Adjacent minute bars share the boundary clock time; next-open may
        # equal the prior close timestamp but must belong to a later bar.
        if order['state']=='filled' and (order['time']<order['signal_time'] or order['bar_close_time']<=order['signal_time']):raise ValueError('成交使用了信号可见前或同根K线')
    digest=hashlib.sha256(json.dumps([[b.closed_at,b.open,b.high,b.low,b.close,b.volume] for b in closed]).encode()).hexdigest()
    return {'symbol':code,'period':period,'resolution':resolution,'bars':len(closed),'first':closed[0].closed_at,'last':closed[-1].closed_at,
            **definition_fields(period,resolution),
            'chart_context':chart_context(code,period,closed,digest),
            'chart_bars':[{'time':int(datetime.fromisoformat(bar.closed_at).timestamp())+8*3600,'source_index':bar.pos,
                           'date_cn':bar.closed_at[:16].replace('T',' '),'open':bar.open,'high':bar.high,'low':bar.low,
                           'close':bar.close,'volume':bar.volume,'is_closed':True} for bar in closed],
            'analysis_eligible':not insufficient,'insufficient_reason':'少于3根已闭合K线，无足够结构证据；空仓结果不构成策略有效性验证' if insufficient else None,
            'source':metadata['source'],'adjustment':metadata['adjustment'],'input_sha256':digest,
            'signal_classes':class_stats,'portfolio_metrics':fills['metrics'],'portfolio_trades':fills['trades'],
            'portfolio_orders':fills['orders'],'portfolio_equity':fills['equity'],'portfolio_settings':fills['settings'],
            'portfolio_limitations':fills['limitations'],'replay':replay,'execution_allowed':False,
            'definition_mode':replay['definition_mode'],'strict_original_equivalence_proven':False,
            'accuracy_note':'规则复现、前缀可知时刻和交易成交单独核验；交易胜率不等于买卖点定义准确率'}


def start(code,resolution,periods=None):
    if resolution not in {'stroke','segment'}:raise HTTPException(422,'选择笔级或线段级')
    periods=PERIODS if periods is None else periods
    if not isinstance(periods,list) or not periods or len(periods)>len(PERIODS) or any(period not in PERIODS for period in periods) or len(set(periods))!=len(periods):raise HTTPException(422,'回测周期无效')
    with lock:
        same=next((item for item in runs.values() if item['symbol']==code and item['resolution']==resolution and item['periods']==periods and item['state'] in {'queued','running'}),None)
        if same:return dict(same)
        if any(item['state'] in {'queued','running'} for item in runs.values()):raise HTTPException(429,'精细回测正在运行，请等待当前任务')
        ident=uuid.uuid4().hex
        run={'id':ident,'symbol':code,'resolution':resolution,'periods':periods,'state':'queued','progress':0,'rows':[],
             'completed':0,'total':len(periods),'current_period':None,'created_at':datetime.now(tdx.CN).isoformat()}
        runs[ident]=run
    def work():
        try:
            with lock:run['state']='running'
            now=datetime.now(tdx.CN);daily,dm=tdx.fetch(code,'day',now);daily=[b for b in daily if b.closed]
            for index,period in enumerate(periods):
                with lock:run['current_period']=period
                try:
                    bars,meta=(daily,dm) if period=='day' else tdx.fetch(code,period,now)
                    def report(done,total):
                        with lock:run.update(current_bar=done,current_bars=total,progress=int(100*(index+done/max(total,1))/len(periods)))
                    detail=execute_period(code,period,resolution,bars,meta,daily,dm,report)
                    path=runtime()/ident/(period+'.json.gz');pack(path,detail)
                    row={k:v for k,v in detail.items() if k not in {'replay','portfolio_orders','portfolio_trades','portfolio_equity','chart_bars','chart_context'}}
                    row.update(state='completed',detail_url=f'/api/research/precision-backtests/{ident}/{period}')
                except Exception as error:row={'period':period,'state':'failed','error':str(error)[:500]}
                with lock:run['rows']=run['rows']+[row];run['completed']+=1
                pack(runtime()/ident/'summary.json.gz',dict(run))
            with lock:run.update(state='completed',progress=100,finished_at=datetime.now(tdx.CN).isoformat())
            pack(runtime()/ident/'summary.json.gz',dict(run))
            # Only bounded summaries are retained in memory; details live on disk.
            with lock:
                while len(runs)>8:runs.pop(next(iter(runs)))
        except Exception as error:
            with lock:run.update(state='failed',error=str(error)[:500])
    pool.submit(work);return dict(run)


def status(ident):
    if len(ident)!=32 or any(ch not in '0123456789abcdef' for ch in ident):raise HTTPException(422,'回测任务标识无效')
    with lock:
        if ident in runs:return copy.deepcopy(runs[ident])
    path=ARCHIVE/ident/'summary.json.gz'
    if not path.is_file():path=runtime()/ident/'summary.json.gz'
    if path.is_file():return json.loads(gzip.decompress(path.read_bytes()))
    raise HTTPException(404,'回测任务不存在或临时存储已清理')


def detail(ident,period):
    if len(ident)!=32 or any(ch not in '0123456789abcdef' for ch in ident) or period not in PERIODS:raise HTTPException(422,'回测结果标识无效')
    path=ARCHIVE/ident/(period+'.json.gz')
    if not path.is_file():path=runtime()/ident/(period+'.json.gz')
    if not path.is_file():raise HTTPException(404,'本周期回测尚未完成')
    return json.loads(gzip.decompress(path.read_bytes()))


def available(code,resolution):
    if resolution not in {'stroke','segment'}:raise HTTPException(422,'回测结构级别无效')
    index=ARCHIVE/'manifest.json'
    if not index.is_file():raise HTTPException(404,'此股票暂未保存完整回测，可启动全周期回放')
    manifest=json.loads(index.read_text(encoding='utf-8'))
    item=next((item for item in manifest['runs'] if item['symbol']==code and item['resolution']==resolution),None)
    if not item:raise HTTPException(404,'此股票暂未保存完整回测，可启动全周期回放')
    result=status(item['id']);result['saved_replay']=True;return result
