import React,{Suspense,lazy} from 'react';
import {createRoot} from 'react-dom/client';
import ResearchApp from './research/ResearchApp';
const Legacy=lazy(async()=>{await import('./index.css');return import('./App')});
const legacy=new URLSearchParams(location.search).get('terminal')==='1';
createRoot(document.getElementById('root')!).render(legacy?<Suspense fallback={<p style={{padding:24}}>正在载入行情终端…</p>}><Legacy/></Suspense>:<ResearchApp/>);
