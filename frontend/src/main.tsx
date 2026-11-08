import React,{Suspense,lazy} from 'react';
import {createRoot} from 'react-dom/client';
import {registerSW} from 'virtual:pwa-register';
const ResearchApp=lazy(()=>import('./research/ResearchApp'));
const Legacy=lazy(async()=>{await import('./index.css');return import('./App')});
const legacy=new URLSearchParams(location.search).get('terminal')==='1';
// An existing open tab must reload when the replacement worker takes control.
// Activating a worker alone leaves the old JavaScript running in that tab.
if('serviceWorker' in navigator){
 const controlled=!!navigator.serviceWorker.controller;let reloading=false;
 navigator.serviceWorker.addEventListener('controllerchange',()=>{if(controlled&&!reloading){reloading=true;location.reload()}});
 registerSW({immediate:true,onRegisteredSW(_url,registration){
  const update=()=>{if(!document.hidden)void registration?.update().catch(()=>{})};
  window.addEventListener('focus',update);document.addEventListener('visibilitychange',update);update();
 }});
}
createRoot(document.getElementById('root')!).render(<Suspense fallback={<p style={{padding:24}}>正在载入工作台…</p>}>{legacy?<Legacy/>:<ResearchApp/>}</Suspense>);
