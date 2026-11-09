import React,{forwardRef,useEffect,useImperativeHandle,useRef,useState} from 'react';
import {createChart,CandlestickSeries,LineSeries,HistogramSeries,ColorType,type IChartApi} from 'lightweight-charts';
import type {Evidence,Layer,Panel} from './types';
import {CLASSES,fmt} from './types';
import {signalStatus} from './signalDisplay';

export interface ChartActions {fit:()=>void;recent:()=>void;zoom:(direction:number)=>void;exportPNG:()=>Promise<void>}
interface Props {panel:Panel;layers:Set<Layer>;onEvidence:(x:Evidence)=>void;focus:Evidence|null;fullScreen:boolean}
const COLORS=['#329b8d','#8972b2','#b98b40','#507caf'];
export const ChartPane=forwardRef<ChartActions,Props>(function ChartPane({panel:p,layers,onEvidence,focus,fullScreen},ref){
 const mainEl=useRef<HTMLDivElement>(null),volEl=useRef<HTMLDivElement>(null),macdEl=useRef<HTMLDivElement>(null),svgEl=useRef<SVGSVGElement>(null);
 const handles=useRef<any>(null),dataRef=useRef(p);dataRef.current=p;
 const savedViewport=useRef<any>(null);
 const [geometry,setGeometry]=useState<any>(null),[hover,setHover]=useState<Evidence|null>(null);
 const [original,setOriginal]=useState(''),[rank,setRank]=useState(0);
 const line=p.kind==='line',bars:any[]=line?(p.points||[]):(p.bars||[]);
 const originals=(p.abcd||[]).filter((x:any)=>x.mode==='a+A+b+B+c_then_d');
 const points=p.display_signals||p.signals||[];
 useEffect(()=>{setOriginal(originals.at(-1)?.id||'');setRank(0)},[p]);
 useEffect(()=>{
  if(!mainEl.current||!volEl.current||!macdEl.current||!bars.length)return;
  let disposed=false,sync=false,raf=0;
  const make=(el:HTMLElement,time:boolean)=>createChart(el,{width:el.clientWidth,height:el.clientHeight,layout:{background:{type:ColorType.Solid,color:'#ffffff'},textColor:'#73869a',fontFamily:'system-ui,Microsoft YaHei,sans-serif',fontSize:11,attributionLogo:el===mainEl.current},grid:{vertLines:{color:'#f0f4f8'},horzLines:{color:'#eef3f7'}},rightPriceScale:{borderColor:'#e2e9f0',minimumWidth:66,scaleMargins:{top:.13,bottom:.12}},timeScale:{visible:time,timeVisible:line||p.period.endsWith('m'),secondsVisible:false,borderColor:'#e2e9f0',minBarSpacing:.01,tickMarkFormatter:(t:any,type:any)=>{const iso=new Date(Number(t)*1000).toISOString();return type<=2?iso.slice(2,10):iso.slice(11,16)}},localization:{locale:'zh-CN',timeFormatter:(t:any)=>new Date(Number(t)*1000).toISOString().replace('T',' ').slice(0,16)},crosshair:{mode:0},handleScroll:{mouseWheel:true,pressedMouseMove:true,horzTouchDrag:true,vertTouchDrag:false},handleScale:{axisPressedMouseMove:true,mouseWheel:true,pinch:true}});
  const main=make(mainEl.current,false),volume=make(volEl.current,line),macd=make(macdEl.current,true);const charts=[main,volume,macd];
  const price=main.addSeries(line?LineSeries:CandlestickSeries,(line?{color:'#3674a8',lineWidth:2}:{upColor:'#d7515c',downColor:'#16917b',borderUpColor:'#d7515c',borderDownColor:'#16917b',wickUpColor:'#d7515c',wickDownColor:'#16917b'}) as any);
  price.setData(bars.map((b:any)=>line?{time:b.time,value:b.value}:{time:b.time,open:b.open,high:b.high,low:b.low,close:b.close,...(b.is_closed===false?{color:'#9baabc',borderColor:'#9baabc',wickColor:'#9baabc'}:{})}) as any);
  const vol=volume.addSeries(HistogramSeries,{priceFormat:{type:'volume'},priceLineVisible:false,lastValueVisible:false});
  vol.setData(bars.map((b:any,i:number)=>({time:b.time,value:b.volume||0,color:(line?i>0&&b.value<bars[i-1].value:b.close<b.open)?'#72b9a68c':'#df969e8c'})) as any);
  const hist=macd.addSeries(HistogramSeries,{lastValueVisible:false,priceLineVisible:false});hist.setData((p.macd||[]).map((b:any)=>({time:b.time,value:b.histogram,color:b.histogram>=0?'#df969e99':'#72b9a699'})));
  for(const [field,color] of [['dif','#b68b37'],['dea','#8d74ad']]){const s=macd.addSeries(LineSeries,{color,lineWidth:1,lastValueVisible:false,priceLineVisible:false});s.setData((p.macd||[]).map((b:any)=>({time:b.time,value:b[field]})))}
  const update=()=>{cancelAnimationFrame(raf);raf=requestAnimationFrame(()=>{const host=mainEl.current;if(disposed||!host)return;const range=main.timeScale().getVisibleLogicalRange();if(!range)return;setGeometry({range,width:host.clientWidth,height:host.clientHeight,pw:host.clientWidth-main.priceScale('right').width(),x:(i:number)=>main.timeScale().logicalToCoordinate(i as any),y:(v:number)=>price.priceToCoordinate(v),tick:performance.now()});})};
  charts.forEach(c=>c.timeScale().subscribeVisibleLogicalRangeChange(r=>{if(!r||sync)return;sync=true;charts.filter(o=>o!==c).forEach(o=>o.timeScale().setVisibleLogicalRange(r));sync=false;update()}));
  main.subscribeCrosshairMove(param=>{const found=param.seriesData.get(price) as any;setHover(found?{...found,date:typeof param.time==='number'?new Date(param.time*1000).toISOString().replace('T',' ').slice(0,16):''}:null)});
  const resize=new ResizeObserver(()=>{for(const [i,el]of [mainEl.current,volEl.current,macdEl.current].entries()){if(el)charts[i].resize(el.clientWidth,el.clientHeight)}update()});[mainEl.current,volEl.current,macdEl.current].forEach(x=>x&&resize.observe(x));
  const recent=()=>main.timeScale().setVisibleLogicalRange({from:Math.max(-1,bars.length-(p.display_session_count?240*p.display_session_count:window.innerWidth<600?90:220)),to:bars.length+6});
  const latest=points.at(-1);
  const viewKey=p.symbol+':'+p.period+':'+p.source_kind,previous=savedViewport.current;
  if(previous?.key===viewKey&&previous.range&&!previous.follow)main.timeScale().setVisibleLogicalRange(previous.range);
  else if(!line&&latest&&layers.has('signals'))main.timeScale().setVisibleLogicalRange({from:Math.max(-1,latest.anchor-100),to:Math.min(bars.length+6,latest.anchor+100)});
  else recent();
  handles.current={charts,main,price,recent,update};update();
  return()=>{const range=main.timeScale().getVisibleLogicalRange();savedViewport.current={key:viewKey,range,follow:range?range.to>=bars.length-2:true};disposed=true;cancelAnimationFrame(raf);resize.disconnect();charts.forEach(c=>c.remove());handles.current=null;setGeometry(null)};
 },[p]);
 useEffect(()=>{handles.current?.update()},[layers,original,rank,fullScreen]);
 useEffect(()=>{if(!focus||!handles.current)return;setHover(null);const anchor=focus.anchor??focus.observed_index??focus.source??focus.end??0;const end=focus.event==='confirmed'?Math.max(anchor,focus.observed_index):anchor;const start=CLASSES[focus.class]?Math.max(0,anchor-80):focus.point?.terminal_range?.[0]??focus.start??Math.max(0,anchor-90);handles.current.main.timeScale().setVisibleLogicalRange({from:Math.max(-1,start-25),to:Math.min(bars.length+6,end+70)});handles.current.update()},[focus]);
 useImperativeHandle(ref,()=>({fit:()=>handles.current?.main.timeScale().fitContent(),recent:()=>handles.current?.recent(),zoom:(d)=>{const s=handles.current?.main.timeScale(),r=s?.getVisibleLogicalRange();if(r){const length=(r.to-r.from)*(d>0?.7:1.4);s.setVisibleLogicalRange({from:r.to-length,to:r.to})}},exportPNG:async()=>{
   const h=handles.current;if(!h)return;const chart=h.main.takeScreenshot();const svg=svgEl.current;const result=document.createElement('canvas');result.width=chart.width;result.height=chart.height+94;const ctx=result.getContext('2d')!;ctx.fillStyle='#fff';ctx.fillRect(0,0,result.width,result.height);ctx.fillStyle='#24384d';ctx.font='600 20px system-ui';ctx.fillText(`${p.name} ${p.symbol} · ${p.label} · ${p.resolution==='stroke'?'精细笔级代理':'线段方向'}`,20,30);ctx.font='12px system-ui';ctx.fillStyle='#687e93';ctx.fillText(`数据截至 ${p.data_as_of||p.coverage.last} · ${p.adjustment_note||p.coverage.source}`,20,53);ctx.drawImage(chart,0,70);
   if(svg){const copy=svg.cloneNode(true) as SVGSVGElement;copy.setAttribute('xmlns','http://www.w3.org/2000/svg');const blob=new Blob([new XMLSerializer().serializeToString(copy)],{type:'image/svg+xml;charset=utf-8'});const url=URL.createObjectURL(blob);const img=new Image();await new Promise<void>((resolve,reject)=>{img.onload=()=>resolve();img.onerror=()=>reject(Error('图层导出失败'));img.src=url});ctx.drawImage(img,0,70);URL.revokeObjectURL(url)}
   ctx.font='11px system-ui';ctx.fillText('量测 v3 · TradingView Lightweight Charts · 确认可能随后失效',20,result.height-8);const a=document.createElement('a');a.href=result.toDataURL('image/png');a.download=`量测v3_${p.symbol}_${p.period}.png`;document.body.appendChild(a);a.click();a.remove();
 }}),[p]);
 const shapes:React.ReactNode[]=[];let id=0;
 if(geometry&&(!line||p.structural_ohlc)){const {x,y,pw,height,range}=geometry,lo=Math.floor(range.from),hi=Math.ceil(range.to);const inView=(s:any)=>s.end>=lo&&s.start<=hi;const spot=(i:number)=>i>=lo&&i<=hi;
  const coords=(values:any[])=>values.every(v=>v!==null&&Number.isFinite(v));
  const txt=(xx:number,yy:number,text:string,color:string,size=11)=>coords([xx,yy])&&<text key={'t'+id++} x={Math.max(4,Math.min(pw-65,xx))} y={Math.max(15,Math.min(height-5,yy))} fill={color} fontSize={size} fontFamily="system-ui,Microsoft YaHei" stroke="white" strokeWidth="3" paintOrder="stroke">{text}</text>;
  const path=(s:any,color:string,width:number,dash?:string)=>{if(!inView(s))return;const a=x(s.start),b=x(s.end),c=y(s.start_price),d=y(s.end_price);if(coords([a,b,c,d]))shapes.push(<line key={'l'+id++} x1={a} x2={b} y1={c} y2={d} stroke={color} strokeWidth={width} strokeDasharray={dash} onClick={()=>onEvidence(s)}><title>{s.id} · {s.state}</title></line>)};
  if(layers.has('centers'))for(const c of p.all_centers||p.centers||[]){if(!inView(c))continue;const a=x(c.start),b=x(c.end),top=y(c.zg),bottom=y(c.zd),color=COLORS[Math.max(0,c.rank-1)%4];if(!coords([a,b,top,bottom]))continue;shapes.push(<rect key={'c'+id++} x={a} y={Math.min(top,bottom)} width={Math.max(1,b-a)} height={Math.max(1,Math.abs(bottom-top))} fill={color} fillOpacity={.08} stroke={color} strokeWidth={1.2} strokeDasharray={c.rank>1?'6 3':undefined} onClick={()=>onEvidence(c)}><title>{`L${c.rank} 中枢 ${fmt(c.zd)}—${fmt(c.zg)}`}</title></rect>);if(b-a>105)shapes.push(txt(Math.max(8,a+7),top-7,`L${c.rank} ${fmt(c.zd)}–${fmt(c.zg)}`,color));if(layers.has('outer')){const yy=y(c.gg),zz=y(c.dd);if(coords([yy,zz]))shapes.push(<rect key={'o'+id++} x={a} y={yy} width={Math.max(1,b-a)} height={Math.max(1,zz-yy)} fill="none" stroke={color} strokeOpacity=".35" strokeDasharray="3 4"/>)}}
  if(layers.has('strokes'))for(const s of p.strokes||[]){
   path(s,p.resolution==='stroke'?'#4e7da8':'#9aaec1',p.resolution==='stroke'?1.8:1.1,s.state==='confirmed'?undefined:'3 3');
   if(p.resolution==='stroke'&&spot(s.end)&&coords([x(s.end),y(s.end_price)])){
    shapes.push(<circle key={'sp'+id++} data-stroke-end={s.end} cx={x(s.end)} cy={y(s.end_price)} r={2.6} fill="white" stroke={s.state==='confirmed'?'#4e7da8':'#ba8a46'} onClick={()=>onEvidence({...s,type:'笔端点',note:'笔端点/分型不直接等于一二三类买卖点'})}/>);
    shapes.push(txt(x(s.end)+4,y(s.end_price)+(s.direction==='up'?-10:17),(s.state==='confirmed'?'':'形成中 ')+fmt(s.end_price),s.state==='confirmed'?'#4e7da8':'#ba8a46',9));
   }
  }
  if(layers.has('segments'))for(const s of p.segments||[]){path(s,s.state==='confirmed'?'#3774ab':'#be872e',2.5,s.state==='confirmed'?undefined:'7 5');if(spot(s.end))shapes.push(txt(x(s.end)+6,y(s.end_price)+(s.direction==='up'?-12:18),fmt(s.end_price),s.state==='confirmed'?'#3774ab':'#be872e'))}
  if(layers.has('fractals'))for(const f of p.fractals||[]){if(!spot(f.source))continue;const xx=x(f.source),yy=y(f.price)+(f.kind==='top'?-8:8),top=f.kind==='top';if(!coords([xx,yy]))continue;shapes.push(<path key={'f'+id++} d={top?`M ${xx-3} ${yy-3} L ${xx+3} ${yy-3} L ${xx} ${yy+3} Z`:`M ${xx-3} ${yy+3} L ${xx+3} ${yy+3} L ${xx} ${yy-3} Z`} fill={top?'#bc6c77':'#388e7d'} onClick={()=>onEvidence({...f,type:'分型',confirmation:'由右侧K线提供证据；不是独立买卖点'})}><title>{top?'顶分型':'底分型'} {fmt(f.price)}</title></path>)}
  let lane=0;if(layers.has('signals'))for(const s of points){
   if(!spot(s.anchor))continue;
   const xx=x(s.anchor),yy=y(s.price),color=s.side==='buy'?'#b44461':'#267f82';if(!coords([xx,yy]))continue;
   const ended=s.state==='invalidated'||s.state==='withdrawn',selected=focus?.id===s.id;
   const label=`${CLASSES[s.class]} ${s.resolution==='stroke'?'笔级':'L'+s.rank} ${s.has_confirmation?'规则确认':'候选'}${ended?'·'+(s.state==='invalidated'?'失效':'撤回'):''}`;
   const width=Math.min(pw-8,Math.max(90,label.length*7.2)),left=Math.max(4,Math.min(pw-width-4,xx-width/2));
   const top=Math.max(8,Math.min(height-27,yy+(s.side==='buy'?24+(lane%3)*22:-42-(lane%3)*22)));lane++;
   shapes.push(<g key={'s'+id++} data-signal-class={s.class} data-signal-id={s.id} data-signal-status={signalStatus(s)} role="button" aria-label={`${label} ${fmt(s.price)}`} tabIndex={0} onClick={()=>onEvidence(s)} onKeyDown={e=>{if(e.key==='Enter')onEvidence(s)}} style={{cursor:'pointer'}}>
    <title>{`${CLASSES[s.class]} · ${signalStatus(s)} · ${s.anchor_time||s.event_time||''} · ${fmt(s.price)}`}</title>
    <line x1={xx} y1={yy} x2={Math.max(left+4,Math.min(left+width-4,xx))} y2={s.side==='buy'?top:top+20} stroke={color} strokeWidth={selected?2:1} strokeDasharray={ended?'3 3':undefined}/>
    <circle cx={xx} cy={yy} r={selected?5:3.5} stroke={color} strokeWidth={selected?2:1.3} fill="white"/>
    <rect x={left} y={top} width={width} height={20} rx={4} fill={selected?'#fff2dc':'white'} stroke={color} strokeWidth={selected?2:1} strokeDasharray={ended?'3 2':undefined}/>
    <text x={left+6} y={top+14} fill={color} fontSize={10} fontFamily="system-ui,Microsoft YaHei">{label}</text>
   </g>);
  }
  if(layers.has('abcd'))for(const group of p.abcd||[]){if(group.mode!=='four_consecutive_same_rank'||group.rank!==rank||!inView(group))continue;for(const s of group.letters){path(s,['#5c82b1','#a17b47','#9b6aa5','#3d9b8d']['abcd'.indexOf(s.label)],1.5,'4 3');if(inView(s))shapes.push(txt((Math.max(0,x(s.start))+Math.min(pw,x(s.end)))/2,(y(s.start_price)+y(s.end_price))/2-15,`${s.label} · L${rank}`,'#587e9f',13))}}
  if(layers.has('original')){const g=originals.find((g:any)=>g.id===original);if(g)for(const s of g.letters){if(!inView(s))continue;const color=s.label==='A'?'#2c9b89':s.label==='B'?'#9273b1':s.label==='c'?'#b55d94':s.label==='d'?'#c39132':'#347bb7';if(s.object_kind==='center'){shapes.push(txt(x(s.start)+10,y(s.zg)-22,`${s.label} 中枢`,color,15))}else{path(s,color,3);shapes.push(txt((Math.max(0,x(s.start))+Math.min(pw,x(s.end)))/2,(y(s.start_price)+y(s.end_price))/2-28,s.label+(s.label==='d'?' 后续段':''),color,17))}}}
  if(layers.has('confirmed'))for(const e of p.confirmations||[]){if(!spot(e.observed_index))continue;const xx=x(e.observed_index),bar=bars[e.observed_index],yy=y(bar?.close||e.price),color=e.side==='buy'?'#b44461':'#267f82';if(!coords([xx,yy]))continue;shapes.push(<path key={'cf'+id++} data-confirmed-class={e.class} d={`M ${xx} ${yy-7} l 7 7 l -7 7 l -7 -7 Z`} fill={color} stroke="white" onClick={()=>onEvidence(e)}><title>{`实际确认 ${CLASSES[e.class]} ${e.observed_at}`}</title></path>);shapes.push(txt(xx+10,yy+(e.side==='buy'?42:-38),`确认 ${CLASSES[e.class]} ${e.resolution==='stroke'?'笔级':'L'+e.rank}`,color,11));if(spot(e.anchor))shapes.push(<line key={'link'+id++} x1={x(e.anchor)} y1={y(e.price)} x2={xx} y2={yy} stroke={color} strokeDasharray="2 5"/>) }
 }
 const bar=hover||(focus?bars[focus.event==='confirmed'?focus.observed_index:focus.anchor]:null)||bars.at(-1)||{};
 return <div className={'lc-chart-stack '+(fullScreen?'expanded':'')} data-chart-ready={Boolean(geometry)}>
  {focus&&CLASSES[focus.class]&&<div className="lc-signal-focus">正在定位：{CLASSES[focus.class]} {focus.resolution==='stroke'?'笔级':'L'+focus.rank} · {focus.anchor_time||focus.event_time||bars[focus.anchor]?.date_cn} · {signalStatus(focus)}{focus.confirmed_at?' · 确认于 '+focus.confirmed_at:''}</div>}
  <div className="lc-chart-readout"><span className="mono">{hover?.date||bar.date_cn}</span><span>开 <b>{fmt(bar.open)}</b></span><span>高 <b>{fmt(bar.high)}</b></span><span>低 <b>{fmt(bar.low)}</b></span><span>收 <b>{fmt(line?bar.value:bar.close)}</b></span><span className="readout-help">{line?'价格快照':'滚轮缩放 · 拖动历史 · 点选结构'}</span></div>
  <div className="lc-main-chart"><div ref={mainEl} className="chart-host"/>{geometry&&<svg ref={svgEl} width={geometry.width} height={geometry.height} className="lc-overlays"><defs><clipPath id="lc-clip"><rect width={geometry.pw} height={geometry.height}/></clipPath></defs><g clipPath="url(#lc-clip)">{shapes}</g></svg>}</div>
  <div className="lc-indicator-title">VOL <span>成交量 · 股</span></div><div ref={volEl} className="lc-volume-chart"/>
  {!line&&<><div className="lc-indicator-title">MACD <span>12, 26, 9 · DIF / DEA / 2×柱值</span></div></>}<div ref={macdEl} className={'lc-macd-chart '+(line?'hidden':'')}/>
  {!line&&(layers.has('abcd')||layers.has('original'))&&<div className="lc-abcd-controls"><label>连续四段<select aria-label="ABCD结构级别" value={rank} onChange={e=>setRank(Number(e.target.value))}>{[...new Set((p.abcd||[]).filter((x:any)=>x.mode==='four_consecutive_same_rank').map((x:any)=>x.rank))].map((r:any)=><option key={r} value={r}>L{r} {r===0?'线段':'走势类型'}</option>)}</select></label><label>原文分解<select aria-label="原文ABCD实例" value={original} onChange={e=>{setOriginal(e.target.value);const g=originals.find((x:any)=>x.id===e.target.value);if(g)handles.current?.main.timeScale().setVisibleLogicalRange({from:g.start-20,to:g.end+30})}}><option value="">暂无完整对象</option>{originals.map((g:any)=><option key={g.id} value={g.id}>L{g.rank} · {bars[g.start]?.date_cn?.slice(0,10)} · {g.missing_labels?.length?'含缺项':'a+A+b+B+c+d'}</option>)}</select></label></div>}
 </div>
});
