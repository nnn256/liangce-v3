"""Observed auction snapshots, never reconstructed from continuous-session data."""
from collections import OrderedDict
from datetime import datetime,timedelta,timezone
from pathlib import Path
import json,math,os,threading,time
from fastapi import HTTPException

CN=timezone(timedelta(hours=8));guard=threading.Lock();cache=OrderedDict()


def phase(stamp):
    if stamp.weekday()>4:return 'outside_auction'
    seconds=stamp.hour*3600+stamp.minute*60+stamp.second
    if 33300<=seconds<33600:return 'opening_cancel_allowed'
    if 33600<=seconds<=33900:return 'opening_no_cancel'
    if 53820<=seconds<=54000:return 'closing_auction'
    return 'outside_auction'


def finite(value):
    try:number=float(value)
    except (ValueError,TypeError):return None
    return number if math.isfinite(number) and number>=0 else None


def build(code,raw,now):
    from web.research_api import normalized_quote
    quote=normalized_quote(code,raw,now.isoformat())
    if not quote:raise HTTPException(503,'竞价行情源未返回有效价格；不使用演示价格')
    market=datetime.fromisoformat(quote['market_time']) if quote['market_time'] else None
    fresh=bool(market and 0<=(now-market).total_seconds()<=120)
    quote['stale']=not fresh
    book={}
    for side in ['bids','asks']:
        levels=(raw.get('orderBook') or {}).get(side) or []
        book[side]=[{'level':i+1,'price':finite(levels[i].get('price')) if i<len(levels) else None,
                     'volume_lots':finite(levels[i].get('volume')) if i<len(levels) else None} for i in range(5)]
    day=now.date().isoformat();root=Path(os.environ.get('LIANGCE_RUNTIME',str(Path(__file__).resolve().parents[1]/'.runtime/research')))/'auction'
    file=root/f'{code}_{day}.json'
    samples=[]
    if file.is_file():
        try:samples=json.loads(file.read_text(encoding='utf-8'))
        except (ValueError,OSError):samples=[]
    active=phase(now)!='outside_auction'
    if fresh and phase(market)!='outside_auction' and market.date()==now.date():
        sample={'market_time':market.isoformat(),'received_at':now.isoformat(),'price':quote['price'],'source':quote['source']}
        samples=[item for item in samples if item['market_time']!=sample['market_time']]+[sample]
        samples=sorted(samples,key=lambda item:item['market_time'])[-1200:]
        root.mkdir(parents=True,exist_ok=True)
        tmp=file.with_suffix('.tmp');tmp.write_text(json.dumps(samples,ensure_ascii=False),encoding='utf-8');tmp.replace(file)
        # Bounded temporary storage, including symbols no longer being watched.
        for older in sorted(root.glob('*.json'),key=lambda path:path.stat().st_mtime,reverse=True)[200:]:older.unlink(missing_ok=True)
    points=[{'time':int(datetime.fromisoformat(item['market_time']).timestamp())+8*3600,'value':item['price'],
             'date_cn':item['market_time'][:19].replace('T',' '),'volume':0,'source_index':i} for i,item in enumerate(samples)]
    last=samples[-1]['market_time'] if samples else quote['market_time']
    return {'schema':'liangce.research.v1','symbol':code,'name':quote['name'],'period':'auction','label':'竞价实时快照','kind':'line',
            'points':points,'bars':[],'data_as_of':last or now.isoformat(),'structure_as_of':None,'source_kind':'live_auction_snapshot',
            'fetched_at':now.isoformat(),'computed_at':now.isoformat(),'raw_last_price':quote['price'],
            'coverage':{'count':len(points),'closed_count':0,'forming_count':0,'first':points[0]['date_cn'] if points else None,
                        'last':last,'source':quote['source'],'scope':'observed_auction_snapshots_only','input_sha256':None},
            'auction':{'quote':quote,'order_book':book,'phase':phase(now),'source_phase':phase(market) if market else 'unknown',
                       'collecting':active and fresh,'samples':len(samples),'current_session_date':day,
                       'price_semantics':'行情源当前价格及五档盘口；未认证为虚拟撮合价、匹配量或未匹配量',
                       'history_note':'只记录本服务实际观察到的当日竞价价格；未采集时段不补造，服务重启可能清理临时记录'},
            'provenance':{'source':quote['source'],'confirmation_eligible':False,'snapshot_only':True},
            'strokes':[],'segments':[],'fractals':[],'all_centers':[],'signals':[],'confirmations':[],'confirmation_records':[],
            'signal_events':[],'abcd':[],'macd':[],'portfolio_metrics':None,'portfolio_trades':[],'execution_allowed':False,
            'definition_mode':'auction_quote_snapshot_no_ohlc','strict_original_equivalence_proven':False,
            'refresh_after_seconds':5 if active else 15 if now.weekday()<5 and 550<=now.hour*60+now.minute<=905 else 300,
            'market_session':'trading_hours' if active else 'outside_trading_hours'}


def auction_panel(code,refresh=False):
    import market_gateway as gateway
    now=datetime.now(CN);ttl=2 if phase(now)!='outside_auction' else 15
    with guard:
        saved=cache.get(code)
        if not refresh and saved and time.monotonic()-saved[0]<ttl:return saved[1]
        market=code[2:]+'.'+code[:2].upper()
        try:raw=gateway.fetch_level1_quotes([market]).get(market)
        except Exception as error:raise HTTPException(503,'竞价报价暂不可用：'+str(error)[:100]) from error
        if not raw:raise HTTPException(503,'行情源未返回竞价报价，请稍后重试')
        result=build(code,raw,now);cache[code]=(time.monotonic(),result);cache.move_to_end(code)
        while len(cache)>20:cache.popitem(last=False)
        return result
