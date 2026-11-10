import assert from 'node:assert/strict';
import {createLivePoller} from './livePolling';
const flush=()=>new Promise(resolve=>setImmediate(resolve));
let pending:(()=>void)|undefined,delay=0,clock=0,calls=0,release:((delay:number)=>void)|undefined;
const controller=createLivePoller({active:()=>true,now:()=>clock,
 schedule:(callback,ms)=>{pending=callback;delay=ms;return 1},cancel:()=>{pending=undefined},
 task:async signal=>{calls++;return new Promise<number>(resolve=>{release=resolve})}});
pending!();await flush();controller.refresh();controller.refresh();assert.equal(calls,1,'Updates cannot overlap');
clock=3000;release!(10000);await flush();assert.equal(delay,250,'Several refreshes queue at most one followup');
pending!();await flush();assert.equal(calls,2);clock=6000;release!(10000);await flush();assert.equal(delay,7000,'Network time is part of the requested refresh cadence');
controller.stop();assert.equal(pending,undefined);
let active=false,ticks=0;
const paused=createLivePoller({active:()=>active,schedule:(cb)=>{pending=cb;return 1},cancel:()=>{pending=undefined},task:async()=>{ticks++;return 10000}});
pending!();await flush();assert.equal(ticks,0);active=true;paused.refresh();await flush();assert.equal(ticks,1);paused.stop();
let aborted=false,reported=0;
const cancelled=createLivePoller({active:()=>true,schedule:cb=>{pending=cb;return 1},cancel:()=>{},onError:()=>reported++,task:signal=>new Promise<number>((_,reject)=>signal.addEventListener('abort',()=>{aborted=true;reject(Error('aborted'))}))});
pending!();await flush();cancelled.stop();await flush();assert.equal(aborted,true);assert.equal(reported,0);
console.log('Live refreshes serialize requests, account for download time, resume and cancel safely.');
