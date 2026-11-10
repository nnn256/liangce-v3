export type Evidence = Record<string, any>;
export interface Bar {time:number;source_index:number;date_cn:string;open:number;high:number;low:number;close:number;volume:number;is_closed:boolean}
export interface Panel extends Evidence {symbol:string;name:string;period:string;kind:'candles'|'line';label:string;bars?:Bar[];points?:Evidence[];coverage:Evidence;confirmations:Evidence[];source_kind:string;data_as_of:string}
export interface Stock {symbol:string;code:string;name:string;market:string;archived?:boolean;price?:number;change_percent?:number}
export interface Quote {symbol:string;name:string;price:number;previous_close:number|null;change:number|null;change_percent:number|null;market_time:string|null;received_at:string;source:string;stale:boolean}
export interface Quotes {quotes:Record<string,Quote>;missing:string[];market_session:string;refresh_after_seconds:number;error:string|null;received_at:string}
export type Layer = 'fractals'|'strokes'|'segments'|'centers'|'signals'|'confirmed'|'abcd'|'original'|'outer';
export const PERIODS=[['timeshare','分时'],['five_days','五日分时'],['auction','竞价'],['1m','1分'],['5m','5分'],['15m','15分'],['30m','30分'],['60m','60分'],['day','日K'],['5d','5日K'],['week','周K'],['month','月K'],['quarter','季K'],['year','年K']] as const;
export const CLASSES:Record<string,string>={first_buy:'一买',second_buy:'二买',third_buy:'三买',first_sell:'一卖',second_sell:'二卖',third_sell:'三卖'};
export const STATE:Record<string,string>={snapshot_validated:'历史结构核对',confirmed:'已确认',candidate:'候选',invalidated:'已失效',withdrawn:'已撤回',awaiting_lower_confirmation:'待确认',provisional:'形成中',completed:'已完成',running:'计算中',queued:'排队中',failed:'失败',candidate_observed:'候选出现',confirmed_event:'结构确认',reappeared:'候选重现',formed:'形成',extended:'延伸',broken:'离开不返回',leaving:'等待回试',trend_divergence_supported_candidate:'趋势背驰候选',consolidation_force_weakening:'盘整力度减弱',not_supported:'条件未满足'};
export const fmt=(v:any,d=2)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('zh-CN',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
export const percent=(v:any)=>typeof v==='number'?(v>=0?'+':'')+(v*100).toFixed(2)+'%':'—';
