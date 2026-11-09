import {useEffect,useState} from 'react';
import {Download,LoaderCircle,Play} from 'lucide-react';
import {downloadJSON,request} from './api';
import {CLASSES,PERIODS,percent,type Evidence} from './types';
import {SIGNAL_CLASSES} from './signalDisplay';

interface Props {symbol:string;resolution:'stroke'|'segment';onDetail:(detail:Evidence)=>void}
export function PrecisionBacktests({symbol,resolution,onDetail}:Props){
 const [job,setJob]=useState<Evidence|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[opening,setOpening]=useState('');
 useEffect(()=>{setJob(null);setError('');const control=new AbortController();request('/api/research/saved-replays/'+symbol+'/'+resolution,{},control.signal,15000).then(next=>{if(!control.signal.aborted)setJob(next)}).catch(()=>{});return()=>control.abort()},[symbol,resolution]);
 useEffect(()=>{
  if(!job?.id||!['queued','running'].includes(job.state))return;
  const control=new AbortController();let timer:ReturnType<typeof setTimeout>|undefined;
  const poll=async()=>{try{const next=await request('/api/research/precision-backtests/'+job.id,{},control.signal,15000);setJob(next);if(['queued','running'].includes(next.state))timer=setTimeout(poll,1500)}catch(e:any){if(!control.signal.aborted)setError(e.message)}};
  timer=setTimeout(poll,1000);return()=>{control.abort();clearTimeout(timer)};
 },[job?.id,job?.state]);
 const start=async()=>{setError('');setBusy(true);try{setJob(await request('/api/research/precision-backtests',{method:'POST',body:JSON.stringify({symbol,resolution})},undefined,20000))}catch(e:any){setError(e.message)}finally{setBusy(false)}};
 const open=async(row:Evidence)=>{setOpening(row.period);setError('');try{onDetail(await request(row.detail_url,{},undefined,60000))}catch(e:any){setError(e.message)}finally{setOpening('')}};
 const running=busy||['queued','running'].includes(job?.state);
 return <section className="lc-precision-replay">
  <div className="lc-precision-heading"><div><b>逐根回放与成交回测</b><small>{resolution==='stroke'?'精细笔级代理规则':'线段/递归走势规则'} · 所有闭合K线 · 下一可交易开盘成交</small></div><button onClick={start} disabled={running}>{running?<LoaderCircle size={13} className="spin"/>:<Play size={13}/>}全周期回测</button></div>
  {job&&<div className="lc-replay-progress"><span>{job.saved_replay?'已保存真实回放 · ':''}{job.state==='completed'?'已完成':job.state==='failed'?'失败':'回放中'} {job.completed}/{job.total} · {PERIODS.find(item=>item[0]===job.current_period)?.[1]||''} {job.current_bar??0}/{job.current_bars??0}</span><b>{job.progress}%</b><progress max={100} value={job.progress}/></div>}
  {(error||job?.error)&&<p className="lc-live-error">{error||job?.error}</p>}
  {!!job?.rows?.length&&<><div className="lc-precision-table"><table><thead><tr><th>周期 / 根数</th>{SIGNAL_CLASSES.map(kind=><th key={kind}>{CLASSES[kind]}<small>观察 / 规则确认</small></th>)}<th>已平仓</th><th>净收益</th><th>最大回撤</th><th/></tr></thead><tbody>{job.rows.map((row:any)=><tr key={row.period}><td>{PERIODS.find(item=>item[0]===row.period)?.[1]}<small>{row.bars??'—'}</small></td>{SIGNAL_CLASSES.map(kind=><td key={kind}>{row.signal_classes?row.signal_classes[kind].observed+' / '+row.signal_classes[kind].rule_confirmed:'—'}</td>)}<td>{row.portfolio_metrics?.completed_trades??'—'}</td><td>{row.portfolio_metrics?percent(row.portfolio_metrics.total_return):row.error}</td><td>{row.portfolio_metrics?percent(row.portfolio_metrics.max_drawdown):'—'}</td><td><button disabled={row.state!=='completed'||!!opening} onClick={()=>open(row)}>{opening===row.period?'载入…':'查看点位'}</button></td></tr>)}</tbody></table></div><button className="lc-replay-export" onClick={()=>downloadJSON(job,`${symbol}_${resolution}_全周期回测.json`)}><Download size={13}/>导出回测汇总</button></>}
  <p className="lc-precision-note">规则通过、原文结构完整性和成交收益是三项不同结果。笔级是精细观察代理；回测不在价格锚点倒填成交，包含T+1、100股买入、费用、滑点、涨跌停开盘阻挡和前根成交量约束。粗周期信号在下一日开盘执行。少于3根闭合K线时记录证据不足，空仓收益0不表示策略有效。</p>
 </section>;
}
