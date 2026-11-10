import type {Evidence,Panel} from './types';

export function allStructureLayers(primary:Panel,source:Panel,detail:Evidence|null):Panel{
 const sameInput=primary.coverage.input_sha256===source.coverage.input_sha256;
 const context=detail?.chart_context;
 const original=context?{...primary,...context,signals:context.segment_signals||(sameInput?source.signals:[]),
  confirmations:[],signal_events:[],confirmation_records:[]}:source;
 const fine=context?.stroke_model||(sameInput?source.stroke_model:null);
 const small=primary.resolution==='stroke'?primary:fine?{...primary,...fine,all_centers:fine.centers,confirmations:fine.confirmations||[],signal_events:[],confirmation_records:fine.confirmation_records||[]}:null;
 const large=primary.resolution==='segment'?primary:original;
 const centers=[...(small?.all_centers||[]).map((item:Evidence)=>({...item,resolution:'stroke'})),
  ...(large.all_centers||[]).map((item:Evidence)=>({...item,resolution:'segment'}))];
 return {...primary,structure_view:'both',strokes:small?.strokes||primary.strokes,segments:large.segments||[],
  fractals:small?.fractals||primary.fractals,all_centers:[...new Map(centers.map(item=>[item.id,item])).values()],
  signals:[...(small?.signals||[]),...(large.signals||[])],
  confirmations:[...(small?.confirmations||[]),...(large.confirmations||[])],
  signal_events:[...(small?.signal_events||[]),...(large.signal_events||[])],
  confirmation_records:[...(small?.confirmation_records||[]),...(large.confirmation_records||[])]};
}
