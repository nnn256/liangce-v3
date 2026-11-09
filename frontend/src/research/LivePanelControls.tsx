import {LoaderCircle,RefreshCw} from 'lucide-react';

interface Props {mode:'live'|'archive';onMode:(mode:'live'|'archive')=>void;refresh:()=>void;busy:boolean;updatedAt?:string;error:string;session?:string;forming?:number;count?:number;last?:string}
export function LivePanelControls({mode,onMode,refresh,busy,updatedAt,error,session,forming,count,last}:Props){
 return <section className="lc-live-controls" aria-label="图表数据更新">
  <div className="lc-data-modes"><button aria-pressed={mode==='live'} onClick={()=>onMode('live')}>实时图表</button><button aria-pressed={mode==='archive'} onClick={()=>onMode('archive')}>历史研究 / 确认回测</button></div>
  <div className="lc-live-status" role="status">{mode==='live'?<><span>{busy?<LoaderCircle size={12} className="spin"/>:<i/>}{session==='outside_trading_hours'?'休市 · 最近交易K线':'实时K线自动更新'}</span><span>{updatedAt?'取数 '+updatedAt.slice(11,19):'正在连接行情源'}{last?' · K线截至 '+last.slice(5,16):''}</span><span>{count!=null?'源可用 '+count+' 根':''}{forming?' · '+forming+' 根形成中，不参与结构确认':''}</span></>:<span>已核验历史快照 · 时间固定 · 需要当下行情请切换实时图表</span>}<button onClick={refresh} disabled={busy} aria-label="立即刷新图表"><RefreshCw size={12} className={busy?'spin':''}/>立即刷新</button></div>
  {error&&<p className="lc-live-error">{error}。{mode==='live'?'实时源暂不可用；可切换历史研究，历史数据不会冒充实时行情。':''}</p>}
 </section>;
}
