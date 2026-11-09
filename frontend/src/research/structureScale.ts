import type {Evidence,Panel} from './types';

export interface FractalScale extends Evidence {scale:'fractal'|'stroke'|'segment';scale_label:string;marker_size:number}

export function rangeSize(unit:Evidence,bars:Evidence[]){
 const included=(unit.components||[]).filter((id:unknown)=>typeof id==='string'&&/^k:\d+:\d+$/.test(id as string)).map((id:string)=>id.split(':').slice(1).map(Number));
 const start=Number(unit.start??(included.length?Math.min(...included.map((part:number[])=>part[0])):unit.group_start??unit.source));
 const end=Number(unit.end??(included.length?Math.max(...included.map((part:number[])=>part[1])):unit.group_end??unit.source));
 const values=bars.slice(Math.max(0,start),Math.min(bars.length,end+1));
 const high=values.length?Math.max(...values.map(bar=>bar.high)):unit.high??unit.price;
 const low=values.length?Math.min(...values.map(bar=>bar.low)):unit.low??unit.price;
 return {range_start:start,range_end:end,range_bars:Math.max(0,end-start+1),range_high:high,range_low:low,
  range_amplitude_percent:low>0?(high-low)/low*100:0,
  ...(typeof unit.zd==='number'?{core_height:unit.zg-unit.zd,core_width_percent:unit.zd>0?(unit.zg-unit.zd)/unit.zd*100:0}:{})};
}

export function fractalScales(panel:Panel):FractalScale[]{
 const parents=new Map<string,{unit:Evidence;scale:'stroke'|'segment'}[]>();
 for(const [list,scale] of [[panel.strokes,'stroke'],[panel.segments,'segment']] as const){
  for(const unit of list||[])for(const [side,index] of [['start',unit.start],['end',unit.end]] as const){
   const kind=(side==='end'?unit.direction==='up':unit.direction==='down')?'top':'bottom';
   const key=index+':'+kind;parents.set(key,[...(parents.get(key)||[]),{unit,scale}]);
  }
 }
 const bars=panel.bars||[];
 return (panel.fractals||[]).map((fractal:Evidence)=>{
  const members=parents.get(fractal.source+':'+fractal.kind)||[];
  const ordered=[...members].sort((a,b)=>Number(b.scale==='segment')-Number(a.scale==='segment')||Number(b.unit.state==='confirmed')-Number(a.unit.state==='confirmed'));
  const chosen=ordered[0],scale=chosen?.scale||'fractal';
  const confirmed=chosen?chosen.unit.state==='confirmed':fractal.state==='closed_basis';
  const label=scale==='segment'?'大 · 段端分型':scale==='stroke'?'中 · 笔端分型':'小 · K线分型';
  return {...fractal,...rangeSize(chosen?.unit||fractal,bars),scale,scale_label:label,marker_size:scale==='segment'?7:scale==='stroke'?5:3,
   parent_structure_id:chosen?.unit.id,parent_structure_state:chosen?.unit.state,
   structural_members:members.map(({unit,scale})=>({id:unit.id,scale,state:unit.state,start:unit.start,end:unit.end,basis_at:unit.basis_at})),
   size_basis:'按当前结构中的K线分型、笔端与段端分层；大小不是跨周期或原文递归级别认证',
   size_confirmed_at_index:chosen?Math.max(fractal.basis_at,chosen.unit.basis_at):fractal.basis_at,
   scale_state:confirmed?'结构已完成':'结构形成中',execution_allowed:false};
 });
}
