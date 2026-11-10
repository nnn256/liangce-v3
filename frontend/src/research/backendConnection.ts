export class BackendIdentityError extends Error {}

export function retryableConnection(error:unknown){
 const status=typeof error==='object'&&error!==null&&'status' in error?Number(error.status):0;
 return !(error instanceof BackendIdentityError)&&(!status||status>=500||[408,425,429].includes(status));
}

export function connectionPause(milliseconds:number,signal?:AbortSignal){
 return new Promise<void>((resolve,reject)=>{
  if(signal?.aborted){reject(signal.reason);return}
  const abort=()=>{clearTimeout(timer);reject(signal?.reason)};
  const timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve()},milliseconds);
  signal?.addEventListener('abort',abort,{once:true});
 });
}

interface Options<T> {
 request:()=>Promise<T>;signal?:AbortSignal;active:()=>boolean;
 onRetry?:(failure:unknown)=>void;pause?:(milliseconds:number,signal?:AbortSignal)=>Promise<void>;
}

export async function connectBackend<T>({request,signal,active,onRetry,pause=connectionPause}:Options<T>):Promise<T>{
 let attempts=0;
 // A phone can be the first client to wake a sleeping instance. A slow cold
 // start must not require another device to restart the connection attempt.
 for(;;){
  signal?.throwIfAborted();
  if(!active()){await pause(1000,signal);continue}
  try{return await request()}
  catch(error){
   if(signal?.aborted)throw signal.reason;
   if(!retryableConnection(error))throw error;
   onRetry?.(error);attempts++;
   await pause(attempts<6?1500:10000,signal);
  }
 }
}
