import {ChevronLeft,ChevronRight,LocateFixed} from 'lucide-react';
import {CLASSES,type Evidence} from './types';
import {SIGNAL_CLASSES,signalStatus} from './signalDisplay';

interface Props {signals:Evidence[];selected:string|null;focusedId?:string;diagnostics?:Record<string,Evidence>;resolution?:string;onSelect:(signal:Evidence)=>void;onClass:(kind:string|null)=>void;showAll:()=>void}
export function BuySellSignals({signals,selected,focusedId,diagnostics,resolution='segment',onSelect,onClass,showAll}:Props){
 const group=signals.filter(point=>!selected||point.class===selected);
 const focus=(offset:number)=>{
  if(!group.length)return;
  const index=group.findIndex(point=>point.id===focusedId);
  onSelect(group[index<0?(offset>0?0:group.length-1):(index+(offset>0?1:-1)+group.length)%group.length]);
 };
 return <section className="lc-buy-sell" aria-label="六类买卖点">
  <div className="lc-buy-sell-heading"><b>买卖点</b><span>{resolution==='stroke'?'笔级观察 · 代理规则':'线段/递归走势级'} · 锚点与确认时刻分开</span><button onClick={showAll}>显示全部</button></div>
  <div className="lc-six-signals">{SIGNAL_CLASSES.map(kind=>{
   const points=signals.filter(point=>point.class===kind),confirmed=points.filter(point=>point.has_confirmation).length;
   return <button key={kind} data-signal-class={kind} aria-pressed={selected===kind} className={(kind.endsWith('buy')?'buy':'sell')+(selected===kind?' selected':'')} onClick={()=>{onClass(kind);if(points.length)onSelect(points.at(-1)!)}}>
    <span><b>{CLASSES[kind]}</b><strong>{points.length}</strong></span>
    <small>{points.length?'已确认 '+confirmed+' · 候选 '+(points.length-confirmed):'本周期未形成'}</small>
   </button>
  })}</div>
  <div className="lc-signal-actions"><span>{selected?CLASSES[selected]+'：'+group.length+' 个；'+(group.length?signalStatus(group.at(-1)!):'缺少符合规则的结构证据'):'点击类别定位历史点位，候选和失效点始终保留状态'}</span><div><button aria-label="上一个买卖点" disabled={!group.length} onClick={()=>focus(-1)}><ChevronLeft size={14}/></button><button onClick={()=>{if(group.length)onSelect(group.at(-1)!)}} disabled={!group.length}><LocateFixed size={13}/>最近点位</button><button aria-label="下一个买卖点" disabled={!group.length} onClick={()=>focus(1)}><ChevronRight size={14}/></button></div></div>
  {selected&&diagnostics?.[selected]&&!group.length&&<p className="lc-signal-diagnosis">{diagnostics[selected].reason} · 已收盘K线{diagnostics[selected].bars}根 / 线段{diagnostics[selected].segments} / 中枢{diagnostics[selected].centers}</p>}
 </section>;
}
