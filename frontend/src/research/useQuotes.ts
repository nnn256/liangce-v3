import {useCallback,useEffect,useState} from 'react';
import {backend,request} from './api';
import type {Quote,Quotes} from './types';

export function useQuotes(symbols:string[],enabled:boolean){
 const key=[...new Set(symbols)].sort().join(',');
 const origin=backend();
 const [quotes,setQuotes]=useState<Record<string,Quote>>({}),[error,setError]=useState(''),[loading,setLoading]=useState(false);
 const [session,setSession]=useState(''),[updatedAt,setUpdatedAt]=useState(''),[revision,setRevision]=useState(0);
 const refresh=useCallback(()=>setRevision(value=>value+1),[]);
 useEffect(()=>{
  if(!enabled||!key)return;
  let disposed=false,timer:ReturnType<typeof setTimeout>|undefined,control:AbortController|undefined;
  const run=async()=>{
   if(disposed||document.hidden)return;
   control?.abort();control=new AbortController();setLoading(true);
   let delay=30000;
   try{
    const data=await request<Quotes>('/api/research/quotes?symbols='+encodeURIComponent(key),{},control.signal,45000);
    if(disposed)return;
    setQuotes(data.quotes);setSession(data.market_session);setUpdatedAt(data.received_at);
    setError(data.error||(data.missing.length?'有'+data.missing.length+'只股票暂未返回行情':''));
    delay=data.refresh_after_seconds*1000;
   }catch(e:any){if(!disposed&&e.name!=='AbortError'){setError(e.message);setQuotes(previous=>Object.fromEntries(Object.entries(previous).map(([code,quote])=>[code,{...quote,stale:true}])))} }
   finally{if(!disposed){setLoading(false);timer=setTimeout(run,delay)}}
  };
  const resume=()=>{if(!document.hidden){clearTimeout(timer);void run()}else{clearTimeout(timer);control?.abort()}};
  document.addEventListener('visibilitychange',resume);window.addEventListener('online',resume);
  void run();
  return()=>{disposed=true;clearTimeout(timer);control?.abort();document.removeEventListener('visibilitychange',resume);window.removeEventListener('online',resume)};
 },[key,enabled,revision,origin]);
 return {quotes,error,loading,session,updatedAt,refresh};
}
