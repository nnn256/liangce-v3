"""Explicit adapters for the two user-supplied TDX projects and their units."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
import atexit,calendar,json,os,subprocess,threading,time
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urlencode

from chanmodel.model import Candle

CN=timezone(timedelta(hours=8))
PERIODS={'1m':'minute1','5m':'minute5','15m':'minute15','30m':'minute30','60m':'hour',
         'day':'day','week':'week','month':'month','quarter':'quarter','year':'year','5d':'day'}
ROOT=Path(__file__).resolve().parents[1]
_service=None
_launch_lock=threading.Lock()


def enabled():return bool(os.environ.get('LIANGCE_TDX_API') or os.environ.get('LIANGCE_TDX_BINARY') or os.environ.get('LIANGCE_OPENTDX_PYTHON'))


def rest_origin():
    global _service
    explicit=os.environ.get('LIANGCE_TDX_API')
    if explicit:return explicit.rstrip('/')
    binary=os.environ.get('LIANGCE_TDX_BINARY')
    if not binary:raise ValueError('未配置TDX REST地址或本机桥接程序')
    port=os.environ.get('LIANGCE_TDX_PORT','18081');origin='http://127.0.0.1:'+port
    with _launch_lock:
        if _service is None or _service.poll() is not None:
            if not Path(binary).is_file():raise ValueError('TDX桥接程序不存在')
            _service=subprocess.Popen([binary],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            atexit.register(lambda process=_service:process.terminate() if process.poll() is None else None)
            opener=build_opener(ProxyHandler({}))
            for attempt in range(30):
                try:
                    with opener.open(origin+'/api/health',timeout=.5):break
                except OSError:time.sleep(.1)
            else:raise ValueError('TDX桥接程序启动未就绪')
    return origin


def request(path,parameters=None):
    origin=rest_origin();url=origin+path+('?' +urlencode(parameters) if parameters else '')
    opener=build_opener(ProxyHandler({})) if '127.0.0.1' in origin or 'localhost' in origin else build_opener()
    with opener.open(Request(url,headers={'Accept':'application/json','User-Agent':'LiangceTDX/1'}),timeout=90) as response:
        raw=response.read();data=json.loads(raw)
    if not isinstance(data,dict) or data.get('code')!=0:raise ValueError('TDX接口失败：'+str(data.get('message','invalid envelope'))[:180])
    return data['data']


def period_end(label,period):
    point=datetime.fromisoformat(str(label).replace('Z','+00:00'))
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


def normalize_rest(data,period,now):
    from chanmodel.tdx_data import yuan
    rows=data.get('list',data.get('List'));declared=data.get('count',data.get('Count'))
    if not isinstance(rows,list) or declared is not None and declared!=len(rows):raise ValueError('TDX行数声明与实际不符')
    meta=data.get('meta') or {}
    if meta.get('source') not in {None,'tdx'} or meta.get('type') not in {None,PERIODS[period]}:raise ValueError('TDX返回源/周期不匹配')
    unique={};quarantined=0
    for row in rows:
        label=str(row.get('Time',''));point=period_end(label,period)
        values=[yuan(row.get(key),key) for key in ['Open','High','Low','Close']]
        volume=float(row['Volume'])*100
        if any(value<=0 for value in values):raise ValueError('TDX返回非正价格')
        # Known source anomaly: a zero-activity flat13:00 marker, not a bar.
        if period.endswith('m') and point.hour==13 and point.minute==0 and len(set(values))==1 and volume==0 and float(row.get('Amount',0))==0:
            quarantined+=1;continue
        if period.endswith('m'):
            minute=point.hour*60+point.minute;step=int(period[:-1])
            if not any(start<minute<=end and (minute-start)%step==0 for start,end in [(570,690),(780,900)]):raise ValueError('TDX分钟K线不在闭合时间网格：'+label)
            if point>now+timedelta(minutes=step):raise ValueError('TDX返回未来分钟K线')
        elif str(row['Time'])[:10]>now.date().isoformat():raise ValueError('TDX返回未来日期')
        record=(*values,volume)
        if point in unique and unique[point]!=record:raise ValueError('TDX同一时刻返回冲突K线')
        unique[point]=record
    candles=[Candle(index,*record[:4],point.isoformat(),record[4],point<=now) for index,(point,record) in enumerate(sorted(unique.items()))]
    return candles,{'source':'oficcejo/tdx-api','adjustment':'unadjusted','price_unit':'CNY',
                     'volume_unit':'shares','source_price_unit':'milli_CNY','source_volume_unit':'lots',
                     'scope':'all_provider_native_pages','source_rows':len(rows),'quarantined_zero_activity_rows':quarantined,
                     'provider_meta':meta,'source_retention_unlimited':False}


def split_adjust(code,candles,metadata):
    """Only previously cross-verified splits; do not invent generic adjustments."""
    if code!='sz300949':return candles,metadata
    actions=json.loads((ROOT/'data/research/corporate-actions.json').read_text(encoding='utf-8'))['actions']
    result=[]
    for bar in candles:
        multiplier=1.
        for action in actions:
            if bar.closed_at[:10]>=action['ex_date']:multiplier*=action['share_multiplier']
        result.append(Candle(bar.pos,*[round(value*multiplier,8) for value in [bar.open,bar.high,bar.low,bar.close]],bar.closed_at,bar.volume,bar.closed))
    return result,{**metadata,'adjustment':'causal_split_hfq_verified_actions','corporate_actions':actions,
                   'raw_last_price':candles[-1].close if candles else None,'split_adjustment_verified':True}


def five_day_bars(candles):
    result=[]
    for index in range(0,len(candles),5):
        group=candles[index:index+5]
        complete=len(group)==5 and all(bar.closed for bar in group)
        result.append(Candle(len(result),group[0].open,max(bar.high for bar in group),min(bar.low for bar in group),group[-1].close,
                             group[-1].closed_at,sum(bar.volume or 0 for bar in group),complete))
    return result


def calendar_bars(candles,period,now):
    groups={}
    for bar in candles:
        point=datetime.fromisoformat(bar.closed_at);day=point.date()
        key=(day.isocalendar().year,day.isocalendar().week) if period=='week' else (day.year,day.month) if period=='month' else (day.year,(day.month-1)//3) if period=='quarter' else (day.year,)
        groups.setdefault(key,[]).append(bar)
    result=[]
    for group in groups.values():
        end=period_end(group[-1].closed_at,period)
        result.append(Candle(len(result),group[0].open,max(bar.high for bar in group),min(bar.low for bar in group),group[-1].close,
                             end.isoformat(),sum(bar.volume or 0 for bar in group),end<=now and all(bar.closed for bar in group)))
    return result


def fetch(code,period,now):
    if period not in PERIODS:raise ValueError('此视图不是原生OHLC周期，不能强行生成缠论买卖点')
    # A corporate action inside a month/quarter cannot adjust its whole native
    # candle with one multiplier. Aggregate consistently adjusted daily bars.
    source_period='day' if code=='sz300949' and period in {'week','month','quarter','year','5d'} else period
    if os.environ.get('LIANGCE_OPENTDX_PYTHON') and not (os.environ.get('LIANGCE_TDX_API') or os.environ.get('LIANGCE_TDX_BINARY')):
        process=subprocess.run([os.environ['LIANGCE_OPENTDX_PYTHON'],str(ROOT/'scripts/opentdx_worker.py'),code,source_period],
                               capture_output=True,text=True,encoding='utf-8',timeout=100)
        if process.returncode:raise ValueError('opentdx取数失败：'+process.stderr[-200:])
        payload=json.loads(process.stdout)
        rows=[{'Time':row['time'],'Open':round(row['open']*1000),'High':round(row['high']*1000),'Low':round(row['low']*1000),'Close':round(row['close']*1000),'Volume':row['volume']/100} for row in payload['bars']]
        data={'list':rows,'count':len(rows),'meta':{'source':'tdx','type':PERIODS[source_period]}}
        candles,meta=normalize_rest(data,'day' if source_period=='5d' else source_period,now);meta['source']='acb6104/opentdx'
    else:
        data=request('/api/kline-all/tdx',{'code':code,'type':PERIODS[source_period]})
        candles,meta=normalize_rest(data,'day' if source_period=='5d' else source_period,now)
    candles,meta=split_adjust(code,candles,meta)
    if period=='5d':candles=five_day_bars(candles);meta.update(aggregation='five_contiguous_trade_sessions_from_listing',scope='all_provider_day_bars_grouped_5')
    elif source_period!=period:
        candles=calendar_bars(candles,period,now);meta.update(aggregation='calendar_'+period+'_from_consistently_adjusted_daily',scope='all_provider_day_bars_calendar_aggregate')
    return candles,meta
