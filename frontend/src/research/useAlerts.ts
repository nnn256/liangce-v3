import {useEffect,useRef,useState} from 'react';
import {request} from './api';
import {evaluatePrice,evaluateSignals,type AlertEvent,type AlertRule,type AlertState} from './alertEngine';
import type {Evidence,Quotes} from './types';

function read<T>(key:string,fallback:T):T{try{return JSON.parse(localStorage.getItem(key)||'null')??fallback}catch{return fallback}}
const RULES='liangce.alertRules.v1',STATES='liangce.alertStates.v1',EVENTS='liangce.alertEvents.v1';
export function useAlerts(enabled:boolean){
 const [rules,setRules]=useState<AlertRule[]>(()=>read(RULES,[])),[events,setEvents]=useState<AlertEvent[]>(()=>read(EVENTS,[]));
 const [status,setStatus]=useState('尚未添加提醒'),[error,setError]=useState(''),[checkedAt,setCheckedAt]=useState(''),[revision,setRevision]=useState(0);
 const [desktop,setDesktop]=useState(false),[sound,setSound]=useState(false),[permission,setPermission]=useState(()=>typeof Notification==='undefined'?'unsupported':Notification.permission);
 const states=useRef<Record<string,AlertState>>(read(STATES,{})),audio=useRef<AudioContext|null>(null),delivery=useRef({desktop,sound});delivery.current={desktop,sound};
 const emit=(proposed:AlertEvent[])=>{
  const saved=read<AlertEvent[]>(EVENTS,[]),known=new Set(saved.map(item=>item.id));
  const items=proposed.filter(item=>!known.has(item.id));
  if(!items.length)return;
  setEvents(previous=>{const next=[...items,...previous].slice(0,200);localStorage.setItem(EVENTS,JSON.stringify(next));return next});
  if(delivery.current.sound&&audio.current){try{const oscillator=audio.current.createOscillator(),gain=audio.current.createGain();gain.gain.value=.08;oscillator.frequency.value=880;oscillator.connect(gain);gain.connect(audio.current.destination);oscillator.start();oscillator.stop(audio.current.currentTime+.25)}catch{}}
  if(delivery.current.desktop&&typeof Notification!=='undefined'&&Notification.permission==='granted')for(const item of items.slice(0,3)){
   if('serviceWorker' in navigator)void navigator.serviceWorker.ready.then(reg=>reg.showNotification(item.title,{body:item.body,tag:item.id,icon:new URL('icon.svg',location.href).href})).catch(()=>setError('系统通知未能显示，提醒已保留在页面记录。'));
   else try{new Notification(item.title,{body:item.body,tag:item.id})}catch{setError('系统通知未能显示，提醒已保留在页面记录。')}
  }
 };
 const emitRef=useRef(emit);emitRef.current=emit;
 useEffect(()=>{localStorage.setItem(RULES,JSON.stringify(rules))},[rules]);
 useEffect(()=>{
  const active=rules.filter(rule=>rule.enabled);
  if(!active.length){setStatus('尚未开启提醒');return}
  if(!enabled){setStatus('等待后端连接，连接后自动监控');return}
  let disposed=false,timer:ReturnType<typeof setTimeout>|undefined,running=false;const control=new AbortController();let signalDue=0;
  const run=async()=>{
   if(disposed||running)return;
   if(navigator.onLine===false){setStatus('网络离线，等待恢复');timer=setTimeout(run,10000);return}
   const started=Date.now();running=true;setError('');const failures:string[]=[];let interval=300000;
   try{
    const prices=active.filter(rule=>rule.kind==='price');
    if(prices.length){try{
     const data=await request<Quotes>('/api/research/quotes?symbols='+encodeURIComponent([...new Set(prices.map(rule=>rule.symbol))].join(',')),{cache:'no-store'},control.signal,45000);
     if(disposed)return;interval=data.refresh_after_seconds*1000;
     for(const rule of prices){const result=evaluatePrice(rule,states.current[rule.id]||{},data.quotes[rule.symbol],Date.now());states.current[rule.id]=result.state;emitRef.current(result.events)}
     if(data.missing.length||data.error)failures.push(data.error||'部分监控股票缺少新报价');
    }catch(e:any){if(!control.signal.aborted){failures.push(e.message);interval=Math.min(interval,10000)}}}
    const signals=active.filter(rule=>rule.kind==='signal');
    if(signals.length&&Date.now()>=signalDue){
     const groups=new Map<string,AlertRule[]>();for(const rule of signals){const key=rule.symbol+'/'+rule.period+'?resolution='+rule.resolution;groups.set(key,[...(groups.get(key)||[]),rule])}
     let next=300000;
     for(const [key,items] of groups){try{
      const data=await request<Evidence>('/api/research/monitor-signals/'+key,{cache:'no-store'},control.signal,90000);if(disposed)return;
      next=Math.min(next,data.refresh_after_seconds*1000);
      for(const rule of items){const result=evaluateSignals(rule,states.current[rule.id]||{},data,Date.now());states.current[rule.id]=result.state;emitRef.current(result.events)}
     }catch(e:any){if(!control.signal.aborted){failures.push(items[0].name+'：'+e.message);next=Math.min(next,10000)}}}
     signalDue=Math.max(Date.now()+250,started+next);
    }
    if(signals.length)interval=Math.min(interval,Math.max(1000,signalDue-Date.now()));
    if(!disposed){localStorage.setItem(STATES,JSON.stringify(states.current));setCheckedAt(new Date().toISOString());setStatus(document.hidden?'页面在后台，浏览器可能暂停监控':'监控运行中 · 仅提醒新增事件');setError(failures.join('；'))}
   }finally{running=false;if(!disposed)timer=setTimeout(run,document.hidden?Math.max(interval,60000):Math.max(250,interval-(Date.now()-started)))}
  };
  const resume=()=>{if(!document.hidden){clearTimeout(timer);signalDue=0;void run()}};
  document.addEventListener('visibilitychange',resume);window.addEventListener('online',resume);void run();
  return()=>{disposed=true;control.abort();clearTimeout(timer);document.removeEventListener('visibilitychange',resume);window.removeEventListener('online',resume)};
 },[rules,enabled,revision]);
 const add=(rule:Omit<AlertRule,'id'|'created_at'|'enabled'>)=>{
  if(rules.length>=20)throw Error('最多保存20条提醒，请删除不用的规则');
  if(rule.kind==='signal'&&rules.filter(item=>item.kind==='signal'&&item.enabled).length>=4)throw Error('当前最多同时运行4条信号监控');
  setRules(previous=>[...previous,{...rule,id:crypto.randomUUID(),created_at:new Date().toISOString(),enabled:true}]);
 };
 const toggle=(id:string)=>{const rule=rules.find(rule=>rule.id===id);if(rule&&!rule.enabled&&rule.kind==='signal'&&rules.filter(item=>item.kind==='signal'&&item.enabled).length>=4)throw Error('最多同时运行4条信号监控');delete states.current[id];setRules(previous=>previous.map(rule=>rule.id===id?{...rule,enabled:!rule.enabled}:rule))};
 const remove=(id:string)=>{delete states.current[id];localStorage.setItem(STATES,JSON.stringify(states.current));setRules(previous=>previous.filter(rule=>rule.id!==id))};
 const enableNotifications=async()=>{if(typeof Notification==='undefined'){setPermission('unsupported');return}try{const next=await Notification.requestPermission();setPermission(next);setDesktop(next==='granted')}catch{setPermission('denied');setDesktop(false)}};
 const enableSound=async()=>{if(!audio.current)audio.current=new AudioContext();await audio.current.resume();setSound(previous=>!previous)};
 const test=()=>emit([{id:'test:'+Date.now(),rule_id:'test',symbol:'',name:'测试',kind:'price',title:'量测 · 提醒测试',body:'页面已收到测试提醒；系统通知和声音以授权与开关状态为准。这不是行情触发。',time:new Date().toISOString(),market_time:new Date().toISOString(),price:0,test:true}]);
 return {rules,events,status,error,checkedAt,desktop,sound,permission,add,toggle,remove,enableNotifications,enableSound,test,
  refresh:()=>setRevision(value=>value+1),clear:()=>{setEvents([]);localStorage.removeItem(EVENTS)}};
}
export type AlertsController=ReturnType<typeof useAlerts>;
