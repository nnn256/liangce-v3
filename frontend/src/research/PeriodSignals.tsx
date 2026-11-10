import {useEffect,useState} from 'react';
import {LoaderCircle,ScanLine} from 'lucide-react';
import {request} from './api';
import {CLASSES,PERIODS,type Evidence} from './types';
import {SIGNAL_CLASSES} from './signalDisplay';
import {createLivePoller} from './livePolling';

export function PeriodSignals({symbol,live,onPeriod}:{symbol:string;live:boolean;onPeriod:(period:string)=>void}){
 const [active,setActive]=useState(false),[report,setReport]=useState<Evidence|null>(null),[error,setError]=useState(''),[revision,setRevision]=useState(0);
 useEffect(()=>{setActive(false);setReport(null);setError('')},[symbol]);
 useEffect(()=>{
  if(!active||!live)return;
  const poller=createLivePoller({active:()=>!document.hidden&&navigator.onLine!==false,onError:(error:any)=>setError(error.message),
   task:async(signal)=>{const next=await request('/api/research/period-signals/'+symbol,{cache:'no-store'},signal,20000);if(signal.aborted)return 10000;setReport(next);setError('');return next.state==='running'?1500:(next.refresh_after_seconds||30)*1000}});
  const resume=()=>{if(document.hidden)poller.pause();else poller.refresh()};document.addEventListener('visibilitychange',resume);window.addEventListener('online',resume);
  return()=>{poller.stop();document.removeEventListener('visibilitychange',resume);window.removeEventListener('online',resume)};
 },[active,symbol,live,revision]);
 return <section className="lc-period-signal-scan">
  <div><span>所有K线周期共用六类规则</span><button onClick={()=>{setError('');setActive(true);setRevision(value=>value+1)}} disabled={active&&report?.state!=='completed'&&!error}>{active&&report?.state!=='completed'?<LoaderCircle size={12} className="spin"/>:<ScanLine size={12}/>}检查全部K线{report?' '+report.completed+'/'+report.total:''}</button></div>
  {error&&<p>{error}</p>}
  {report&&<div className="lc-period-scan-table"><table><thead><tr><th>周期</th><th>K线根数</th>{SIGNAL_CLASSES.map(kind=><th key={kind}>{CLASSES[kind]}</th>)}<th>数据截至</th></tr></thead><tbody>{report.rows.map((row:any)=><tr key={row.period} className={row.state==='failed'?'failed':''} onClick={()=>row.state!=='failed'&&onPeriod(row.period)} tabIndex={row.state==='failed'?-1:0} onKeyDown={event=>{if(row.state!=='failed'&&event.key==='Enter')onPeriod(row.period)}}><td>{PERIODS.find(item=>item[0]===row.period)?.[1]}</td><td>{row.bars??'—'}</td>{SIGNAL_CLASSES.map(kind=><td key={kind}>{row.signals?.[kind]??'—'}</td>)}<td>{row.state==='failed'?'失败：'+row.error:row.last}</td></tr>)}</tbody></table></div>}
  {report&&<small>{live?'已开启全部周期自动更新，交易时段约30秒重查，后台暂停。':'历史模式未自动更新。'}表内为闭合K线的真实结构候选数量，点击行定位周期；0表示未形成，失败保留原因。{report.finished_at?' 最近完成 '+report.finished_at.replace('T',' ').slice(0,19):''}</small>}
 </section>;
}
