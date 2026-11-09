import type {Evidence,Panel} from './types';

export const SIGNAL_CLASSES=['first_buy','second_buy','third_buy','first_sell','second_sell','third_sell'] as const;

export function displaySignals(panel:Panel|null):Evidence[]{
 if(!panel)return [];
 const items=new Map<string,Evidence>();
 for(const point of panel.signals||[])items.set(point.id,{...point});
 for(const event of panel.signal_events||[]){
  if(!event.signal_id||!SIGNAL_CLASSES.includes(event.class))continue;
  const item=items.get(event.signal_id)||{...event,id:event.signal_id,state:'candidate',event:undefined};
  if(event.event==='candidate_observed'){
   item.first_seen_at??=event.observed_at;item.first_seen_index??=event.observed_index;
   item.available_time??=event.observed_at;item.available_at??=event.observed_index;
  }
  if(event.event==='invalidated'||event.event==='withdrawn')item.state=event.event;
  items.set(event.signal_id,item);
 }
 for(const confirmation of panel.confirmations||[]){
  const id=confirmation.signal_id;
  const item=items.get(id)||{...confirmation.point,id,class:confirmation.class,rank:confirmation.rank,side:confirmation.side,anchor:confirmation.anchor,price:confirmation.price};
  item.confirmed_at=confirmation.confirmed_at||confirmation.observed_at;
  item.confirmed_index=confirmation.observed_index;item.has_confirmation=true;
  item.confirmation_semantics=confirmation.confirmation_semantics;
  item.confirmation=confirmation;items.set(id,item);
 }
 for(const record of panel.confirmation_records||[]){
  const item=items.get(record.id);if(!item)continue;
  item.state=record.current_state||record.state||item.state;
  item.first_seen_at=record.first_seen_at||item.first_seen_at;
  item.invalidated_at=record.invalidated_at;item.withdrawn_at=record.withdrawn_at;item.audit=record.audit;
 }
 return [...items.values()].map<Evidence>(item=>({
  ...item,event:undefined,signal_id:item.id,
  state:item.state||(item.has_confirmation?'confirmed':'candidate'),
  anchor_time:item.event_time||item.anchor_time||panel.bars?.[item.anchor]?.date_cn,
  observed_at:item.confirmed_at||item.first_seen_at||item.available_time,
 })).filter(item=>SIGNAL_CLASSES.includes(item.class)&&Number.isInteger(item.anchor)&&Number.isFinite(item.price))
 .sort((a,b)=>a.anchor-b.anchor||a.rank-b.rank||a.class.localeCompare(b.class));
}

export function signalStatus(point:Evidence){
 const ended=point.state==='invalidated'?'已失效':point.state==='withdrawn'?'已撤回':'';
 return (point.has_confirmation||point.event==='confirmed'?(point.confirmation_semantics?.startsWith('stroke_rule')?'笔级规则确认':point.confirmation_semantics?.startsWith('current_observation')?'当前证据确认':'历史确认'): '候选')+(ended?' · '+ended:'');
}
