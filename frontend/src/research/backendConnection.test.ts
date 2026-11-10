import assert from 'node:assert/strict';
import {BackendIdentityError,connectBackend,connectionPause} from './backendConnection';

let requests=0,elapsed=0;const delays:number[]=[];
const response=await connectBackend({active:()=>true,request:async()=>{
 requests++;
 if(requests<=8){elapsed+=15000;throw Object.assign(new Error('Instance waking'),{status:503})}
 return {status:'ok'};
},pause:async ms=>{delays.push(ms);elapsed+=ms}});
assert.equal(requests,9,'A slow cold start recovers without another device or user action');
assert.equal(response.status,'ok');assert.equal(delays.at(-1),10000);
assert.ok(elapsed>90000,'Recovery remains possible beyond the former 90-second deadline');

for(const status of [401,403,404]){
 let attempts=0;
 await assert.rejects(connectBackend({active:()=>true,request:async()=>{attempts++;throw {status}},pause:async()=>{throw Error('must not retry')}}));
 assert.equal(attempts,1,'Authorization and configuration errors do not retry forever');
}
await assert.rejects(connectBackend({active:()=>true,request:async()=>{throw new BackendIdentityError('Wrong application')}}),BackendIdentityError);

let active=false,paused=0;
await connectBackend({active:()=>active,request:async()=>{assert.equal(active,true);return true},pause:async()=>{paused++;active=true}});
assert.equal(paused,1,'Hidden/offline clients wait without sending requests');
const control=new AbortController();control.abort(new Error('cancelled'));
await assert.rejects(connectBackend({signal:control.signal,active:()=>true,request:async()=>true}),/cancelled/);
await assert.rejects(connectionPause(10000,control.signal),/cancelled/);
console.log('Sleeping backend recovers after extended retries; visibility, cancellation and authorization stay bounded.');
