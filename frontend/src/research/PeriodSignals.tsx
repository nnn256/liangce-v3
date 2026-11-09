import {useEffect,useState} from 'react';
import {LoaderCircle,ScanLine} from 'lucide-react';
import {request} from './api';
import {CLASSES,PERIODS,type Evidence} from './types';
import {SIGNAL_CLASSES} from './signalDisplay';

export function PeriodSignals({symbol,onPeriod}:{symbol:string;onPeriod:(period:string)=>void}){
 const [active,setActive]=useState(false),[report,setReport]=useState<Evidence|null>(null),[error,setError]=useState('');
 useEffect(()=>{setActive(false);setReport(null);setError('')},[symbol]);
 useEffect(()=>{
  if(!active)return;let disposed=false,timer:ReturnType<typeof setTimeout>|undefined;const control=new AbortController();
  const poll=async()=>{try{const next=await request('/api/research/period-signals/'+symbol,{},control.signal,20000);if(disposed)return;setReport(next);if(next.state==='running')timer=setTimeout(poll,1500)}catch(e:any){if(!disposed)setError(e.message)}};
  void poll();return()=>{disposed=true;control.abort();clearTimeout(timer)};
 },[active,symbol]);
 return <section className="lc-period-signal-scan">
  <div><span>所有K线周期共用六类规则</span><button onClick={()=>{setError('');setActive(true)}} disabled={active&&report?.state!=='completed'&&!error}>{active&&report?.state!=='completed'?<LoaderCircle size={12} className="spin"/>:<ScanLine size={12}/>}检查全部K线{report?' '+report.completed+'/'+report.total:''}</button></div>
  {error&&<p>{error}</p>}
  {report&&<div className="lc-period-scan-table"><table><thead><tr><th>周期</th><th>K线根数</th>{SIGNAL_CLASSES.map(kind=><th key={kind}>{CLASSES[kind]}</th>)}<th>数据截至</th></tr></thead><tbody>{report.rows.map((row:any)=><tr key={row.period} className={row.state==='failed'?'failed':''} onClick={()=>row.state!=='failed'&&onPeriod(row.period)} tabIndex={row.state==='failed'?-1:0} onKeyDown={event=>{if(row.state!=='failed'&&event.key==='Enter')onPeriod(row.period)}}><td>{PERIODS.find(item=>item[0]===row.period)?.[1]}</td><td>{row.bars??'—'}</td>{SIGNAL_CLASSES.map(kind=><td key={kind}>{row.signals?.[kind]??'—'}</td>)}<td>{row.state==='failed'?'失败：'+row.error:row.last}</td></tr>)}</tbody></table></div>}
  {report&&<small>表内为真实结构候选数量，点击该行定位周期；0表示未形成，失败保留原因。分时/竞价价格曲线不冒充OHLC买卖点。</small>}
 </section>;
}
