interface Options {
 task:(signal:AbortSignal)=>Promise<number>;active:()=>boolean;initialDelay?:number;
 onError?:(error:unknown)=>void;onBusy?:(busy:boolean)=>void;
 now?:()=>number;schedule?:(callback:()=>void,ms:number)=>any;cancel?:(timer:any)=>void;
}

export function createLivePoller({task,active,initialDelay=0,onError,onBusy,now=Date.now,schedule=setTimeout,cancel=clearTimeout}:Options){
 let stopped=false,running=false,pending=false,timer:any;const control=new AbortController();
 const plan=(delay:number)=>{cancel(timer);if(!stopped)timer=schedule(()=>void run(),Math.max(250,delay))};
 const run=async()=>{
  if(stopped||!active())return;
  if(running){pending=true;return}
  running=true;onBusy?.(true);const started=now();let delay=10000;
  try{delay=await task(control.signal)}catch(error){if(!stopped&&!control.signal.aborted)onError?.(error)}
  finally{
   running=false;if(!stopped){onBusy?.(false);if(pending){pending=false;plan(0)}else plan(Math.max(250,delay-(now()-started)))}
  }
 };
 timer=schedule(()=>void run(),initialDelay);
 return {refresh:()=>{cancel(timer);void run()},stop:()=>{stopped=true;control.abort();cancel(timer)},pause:()=>cancel(timer)};
}
