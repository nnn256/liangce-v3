import {LoaderCircle,RefreshCw} from 'lucide-react';

interface Props {mode:'live'|'archive';replay?:boolean;auction?:boolean;onMode:(mode:'live'|'archive')=>void;refresh:()=>void;busy:boolean;updatedAt?:string;error:string;session?:string;forming?:number;count?:number;last?:string;source?:string;scope?:string;refreshSeconds?:number}
export function LivePanelControls({mode,replay,auction,onMode,refresh,busy,updatedAt,error,session,forming,count,last,source,scope,refreshSeconds}:Props){
 const live=mode==='live'&&!replay;
 return <section className="lc-live-controls" aria-label="图表数据更新">
  <div className="lc-data-modes"><button aria-pressed={live} onClick={()=>onMode('live')}>实时图表</button><button aria-pressed={!live} onClick={()=>onMode('archive')}>历史研究 / 确认回测</button></div>
  <div className="lc-live-status" role="status">{live?<><span>{busy?<LoaderCircle size={12} className="spin"/>:<i/>}{auction?'竞价价格与盘口自动更新':session==='outside_trading_hours'?'休市 · 最近交易K线':'实时K线自动更新'}{refreshSeconds?' · 每'+refreshSeconds+'秒取数':''}</span><span>{updatedAt?'取数 '+updatedAt.slice(11,19):'正在连接行情源'}{last?' · '+(auction?'报价时间 ':'K线截至 ')+last.replace('T',' ').slice(5,19):''}</span><span>{count!=null?auction?'已采集 '+count+' 条竞价快照':'源可用 '+count+' 根':''}{forming?' · '+forming+' 根形成中，不参与结构确认':''}</span></>:<span>{replay?'历史逐根回放 · 图表时间固定 · 点击实时图表恢复自动取数':'已核验历史快照 · 时间固定 · 需要当下行情请切换实时图表'}</span>}<button onClick={refresh} disabled={busy} aria-label="立即刷新图表"><RefreshCw size={12} className={busy?'spin':''}/>{replay?'获取最新行情':'立即刷新'}</button></div>
  {error&&<p className="lc-live-error">{error}。{mode==='live'?'实时源暂不可用；可切换历史研究，历史数据不会冒充实时行情。':''}</p>}
  {live&&source&&<p className="lc-data-provider">数据源 {source} · {auction?'仅实际采集快照；不生成K线结构确认':scope?.startsWith('all_provider')?'全部可得历史，分钟保留期以源为准 · 已收盘数据独立计算结构':'近期窗口 · 已收盘数据独立计算结构'}</p>}
 </section>;
}
