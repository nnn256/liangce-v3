import React,{Suspense,lazy} from 'react';
import {createRoot} from 'react-dom/client';
const ResearchApp=lazy(()=>import('./research/ResearchApp'));
const Legacy=lazy(async()=>{await import('./index.css');return import('./App')});
const legacy=new URLSearchParams(location.search).get('terminal')==='1';
createRoot(document.getElementById('root')!).render(<Suspense fallback={<p style={{padding:24}}>正在载入工作台…</p>}>{legacy?<Legacy/>:<ResearchApp/>}</Suspense>);
