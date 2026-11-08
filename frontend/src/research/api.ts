import type {Panel,Stock} from './types';
const BASE=import.meta.env.BASE_URL;
export function backend(){return (localStorage.getItem('liangce.api')||import.meta.env.VITE_API_BASE||'').replace(/\/$/,'')}
export function token(){return sessionStorage.getItem('liangce.token')||''}
export function publicStatic(){return location.hostname.endsWith('.github.io')||new URLSearchParams(location.search).get('static')==='1'}
export async function request<T=any>(path:string,options:RequestInit={},signal?:AbortSignal,timeoutMs=12000):Promise<T>{
 if(publicStatic()&&!backend())throw new Error('公开网页使用已核验归档；新计算请在连接设置中填写后端地址');
 const timeout=AbortSignal.timeout(timeoutMs),bounded=signal?AbortSignal.any([signal,timeout]):timeout;
 const response=await fetch(backend()+path,{...options,signal:bounded,headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(token()?{Authorization:'Bearer '+token()}:{}),...options.headers}});
 if(!response.ok){let message='请求失败 '+response.status;try{const b=await response.json();message=typeof b.detail==='string'?b.detail:JSON.stringify(b.detail||b.message||b)}catch{}throw new Error(message)}
 const type=response.headers.get('content-type')||'';if(!type.includes('json'))throw new Error('当前网址未连接研究后端');return response.json();
}
export async function wakeBackend(signal?:AbortSignal){
 if(publicStatic()&&!backend())return request('/api/research/health',{},signal);
 const deadline=Date.now()+90000;let failure:unknown;
 while(Date.now()<deadline){
  if(signal?.aborted)throw signal.reason;
  try{
   const data=await request('/api/research/health',{},signal,Math.min(15000,deadline-Date.now()));
   if(data.status==='ok'&&data.product==='量测 v3')return data;
   throw new Error('服务正在唤醒，尚未返回研究后端状态');
  }catch(error){
   if(signal?.aborted)throw error;
   failure=error;
   if(error instanceof Error&&/401|403|令牌|只读/.test(error.message))throw error;
   await new Promise<void>((resolve,reject)=>{const abort=()=>{clearTimeout(timer);reject(signal?.reason)};const timer=setTimeout(()=>{signal?.removeEventListener('abort',abort);resolve()},1500);signal?.addEventListener('abort',abort,{once:true})});
  }
 }
 throw failure instanceof Error?new Error('后端唤醒未完成，请稍后重试。'+failure.message):new Error('后端唤醒超时，请稍后重试');
}
export async function archivedPanel(symbol:string,period:string,signal?:AbortSignal):Promise<Panel>{
 const manifest=await fetch(BASE+'research/manifest.json',{signal}).then(r=>{if(!r.ok)throw Error('静态研究目录不可用');return r.json()});
 const file=symbol+'__'+period+'.json.gz';const entry=manifest.files.find((x:any)=>x.file===file);if(!entry)throw Error('该股票暂无已核验归档。连接后端后可获取行情并计算。');
 const response=await fetch(BASE+'research/'+file,{signal});if(!response.ok)throw Error('研究数据下载失败');
 const buffer=await response.arrayBuffer();const digest=await crypto.subtle.digest('SHA-256',buffer);const sha=Array.from(new Uint8Array(digest)).map(x=>x.toString(16).padStart(2,'0')).join('');
 if(sha!==entry.sha256)throw Error('研究数据完整性检查失败，请刷新网页');
 const stream=new Blob([buffer]).stream().pipeThrough(new DecompressionStream('gzip'));return JSON.parse(await new Response(stream).text());
}
export async function loadPanel(symbol:string,period:string,signal:AbortSignal):Promise<{panel:Panel;mode:'api'|'archive';notice?:string}>{
 if(publicStatic()&&!backend())return {panel:await archivedPanel(symbol,period,signal),mode:'archive',notice:'公开历史归档 · 新计算需要连接后端'};
 try{return {panel:await request('/api/research/panel/'+symbol+'/'+period,{},signal),mode:'api'}}
 catch(e){if(signal.aborted)throw e;const panel=await archivedPanel(symbol,period,signal);return {panel,mode:'archive',notice:backend()?'后端暂不可用，当前显示已核验历史归档':'公开历史归档 · 新计算需要连接后端'}}
}
export async function searchSymbols(q:string,signal:AbortSignal):Promise<Stock[]>{
 try{return (await request('/api/research/symbols?q='+encodeURIComponent(q),{},signal)).results}
 catch(e){if(signal.aborted)throw e;const data=await fetch(BASE+'research/symbols.json',{signal}).then(r=>r.json());return data.filter((x:Stock)=>x.name.includes(q)||x.code.includes(q)||x.symbol.includes(q)).slice(0,30)}
}
export function downloadJSON(data:any,name:string){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),5000)}
