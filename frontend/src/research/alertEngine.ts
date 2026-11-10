import type {Evidence,Quote} from './types';

export interface AlertRule {id:string;symbol:string;name:string;enabled:boolean;kind:'price'|'signal';created_at:string;
 comparison?:'gte'|'lte';measure?:'price'|'change_percent';threshold?:number;period?:string;resolution?:'stroke'|'segment';classes?:string[];confirmedOnly?:boolean}
export interface AlertState {initialized?:boolean;hit?:boolean;seen?:string[];lastSample?:string}
export interface AlertEvent {id:string;rule_id:string;symbol:string;name:string;kind:'price'|'signal';title:string;body:string;time:string;market_time:string;price:number;period?:string;resolution?:string;signal_class?:string;definition_mode?:string;test?:boolean}
const labels:Record<string,string>={first_buy:'一买',second_buy:'二买',third_buy:'三买',first_sell:'一卖',second_sell:'二卖',third_sell:'三卖'};

export function evaluatePrice(rule:AlertRule,state:AlertState,quote:Quote|undefined,now:number):{state:AlertState;events:AlertEvent[]}{
 const age=quote?.market_time?now-Date.parse(quote.market_time):Infinity;
 if(!rule.enabled||!quote||quote.stale||!Number.isFinite(age)||age<0||age>120000)return {state,events:[]};
 const value=rule.measure==='change_percent'?quote.change_percent:quote.price;
 if(value==null||!Number.isFinite(value)||!Number.isFinite(rule.threshold))return {state,events:[]};
 const sample=quote.market_time+':'+value;if(sample===state.lastSample)return {state,events:[]};
 const hit=rule.comparison==='lte'?value<=rule.threshold!:value>=rule.threshold!;
 const next={...state,initialized:true,hit,lastSample:sample};
 if(!hit||state.hit)return {state:next,events:[]};
 const title=rule.name+' · '+(rule.measure==='change_percent'?'涨跌幅':'价格')+'到达提醒';
 const body=(rule.comparison==='lte'?'低于或等于 ':'高于或等于 ')+rule.threshold+(rule.measure==='change_percent'?'%':' 元')+'；当前 '+value+(rule.measure==='change_percent'?'%':' 元');
 return {state:next,events:[{id:rule.id+':'+sample,rule_id:rule.id,symbol:rule.symbol,name:rule.name,kind:'price',title,body,time:new Date(now).toISOString(),market_time:quote.market_time!,price:quote.price}]};
}

export function signalKey(point:Evidence){return [point.class,point.side,point.rank,point.anchor_time,point.price,point.confirmed?'confirmed':'candidate'].join(':')}

export function evaluateSignals(rule:AlertRule,state:AlertState,data:Evidence,now:number):{state:AlertState;events:AlertEvent[]}{
 if(!rule.enabled)return {state,events:[]};
 const active=(data.signals||[]).filter((point:Evidence)=>rule.classes?.includes(point.class)&&!point.live_preview&&!['invalidated','withdrawn','snapshot_validated','live_preview'].includes(point.state)&&!['snapshot_audit','unfinished_candle_preview'].includes(point.confirmation_origin)&&(!rule.confirmedOnly||point.confirmed));
 const known=new Set(state.seen||[]),added=active.filter((point:Evidence)=>!known.has(signalKey(point)));
 const seen=[...new Set([...(state.seen||[]),...active.map(signalKey)])].slice(-3000);
 const structureTime=Date.parse(data.structure_as_of),fetchTime=data.fetched_at?Date.parse(data.fetched_at):now;
 const fresh=data.market_session==='trading_hours'&&Number.isFinite(structureTime)&&structureTime<=now&&Number.isFinite(fetchTime)&&fetchTime<=now+30000&&now-fetchTime<=120000&&String(data.structure_as_of).slice(0,10)===new Date(now+8*3600000).toISOString().slice(0,10);
 const events:AlertEvent[]=!state.initialized||!fresh?[]:added.map((point:Evidence)=>({
  id:rule.id+':'+signalKey(point),rule_id:rule.id,symbol:rule.symbol,name:rule.name,kind:'signal',
  title:rule.name+' · '+labels[point.class]+(point.confirmed?'规则确认':'候选出现'),
  body:(rule.resolution==='stroke'?'笔级代理':'线段/递归')+' · '+rule.period+' · 锚点价 '+point.price+'；确认可晚于价格发生时刻',
  time:new Date(now).toISOString(),market_time:point.confirmed_at||point.available_time||data.structure_as_of,price:point.price,
  period:rule.period,resolution:rule.resolution,signal_class:point.class,definition_mode:data.definition_mode,
 }));
 return {state:{...state,initialized:true,seen},events};
}
