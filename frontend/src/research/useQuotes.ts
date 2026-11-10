import {useCallback,useEffect,useState} from 'react';
import {backend,request} from './api';
import {createLivePoller} from './livePolling';
import type {Quote,Quotes} from './types';

export function useQuotes(symbols:string[],enabled:boolean){
 const key=[...new Set(symbols)].sort().join(',');
 const origin=backend();
 const [quotes,setQuotes]=useState<Record<string,Quote>>({}),[error,setError]=useState(''),[loading,setLoading]=useState(false);
 const [session,setSession]=useState(''),[updatedAt,setUpdatedAt]=useState(''),[revision,setRevision]=useState(0);
 const refresh=useCallback(()=>setRevision(value=>value+1),[]);
 useEffect(()=>{
  if(!enabled||!key)return;
  const poller=createLivePoller({active:()=>!document.hidden&&navigator.onLine!==false,onBusy:setLoading,
   onError:(error:any)=>{setError(error.message);setQuotes(previous=>Object.fromEntries(Object.entries(previous).map(([code,quote])=>[code,{...quote,stale:true}])))},
   task:async(signal)=>{
    const data=await request<Quotes>('/api/research/quotes?symbols='+encodeURIComponent(key),{cache:'no-store'},signal,45000);
    if(signal.aborted)return 5000;
    setQuotes(data.quotes);setSession(data.market_session);setUpdatedAt(data.received_at);
    setError(data.error||(data.missing.length?'有'+data.missing.length+'只股票暂未返回行情':''));
    return data.refresh_after_seconds*1000;
   }});
  const resume=()=>{if(document.hidden)poller.pause();else poller.refresh()};
  document.addEventListener('visibilitychange',resume);window.addEventListener('online',resume);
  return()=>{poller.stop();document.removeEventListener('visibilitychange',resume);window.removeEventListener('online',resume)};
 },[key,enabled,revision,origin]);
 return {quotes,error,loading,session,updatedAt,refresh};
}
