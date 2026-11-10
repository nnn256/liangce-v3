import type {Evidence,Panel} from './types';

const lists=['fractals','strokes','segments','all_centers','signals'] as const;
function merge(stable:Evidence[],preview:Evidence[]){return [...new Map([...stable,...preview].map(item=>[item.id,item])).values()]}
export function withLivePreview(panel:Panel|null,enabled=true):Panel|null{
 if(!panel||!enabled||!panel.source_kind.startsWith('live_')||!panel.live_preview)return panel;
 const data=panel.live_preview,combined=panel.structure_view==='both';
 const small=panel.resolution==='stroke'||combined?data.stroke:null,large=panel.resolution==='segment'||combined?data.segment:null;
 const previews={fractals:(small||large)?.fractals||[],strokes:(small||large)?.strokes||[],segments:large?.segments||[],
  all_centers:[...(small?.centers||[]).map((item:Evidence)=>({...item,resolution:'stroke'})),...(large?.centers||[]).map((item:Evidence)=>({...item,resolution:'segment'}))],
  signals:[...(small?.signals||[]),...(large?.signals||[])].map((item:Evidence)=>({...item,id:'preview:'+item.id,state:'live_preview',live_preview:true,
    has_confirmation:false,confirmed_at:null,confirmation_origin:'unfinished_candle_preview'}))};
 const tails=[...(small?data.tails?.stroke||[]:[]),...(large?data.tails?.segment||[]:[])];
 const next:Panel={...panel,preview_tails:tails,preview_count:Object.values(previews).reduce((sum,items)=>sum+items.length,0)+tails.length};
 for(const key of lists)next[key]=merge(panel[key]||[],previews[key]);
 return next;
}

export function currentEvidence(selected:Evidence|null,panel:Panel|null):Evidence|null{
 if(!selected||!panel||!panel.source_kind.startsWith('live_'))return selected;
 const id=selected.id||selected.signal_id;
 if(!id)return {...selected,live_checked_at:panel.fetched_at};
 const collection=selected.event==='confirmed'?panel.confirmations||[]:[...(panel.display_signals||panel.signals||[]),...lists.filter(key=>key!=='signals').flatMap(key=>panel[key]||[]),...(panel.features||[]),...(panel.preview_tails||[])];
 const found=collection.find((item:Evidence)=>(item.id||item.signal_id)===id);
 if(!found)return {...selected,state:selected.live_preview?'preview_expired':'object_not_current',live_checked_at:panel.fetched_at,
  current_object_present:false,live_note:'当前快照中已不存在该对象；保留所选历史证据，不作为当前信号'};
 const record=panel.confirmation_records?.find((item:Evidence)=>item.id===id);
 return {...found,...(record||{}),...(record?{confirmation_history:record}:{}),navigation_key:selected.navigation_key,
  live_checked_at:panel.fetched_at,current_object_present:true};
}
