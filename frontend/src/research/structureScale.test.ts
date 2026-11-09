import assert from 'node:assert/strict';
import {fractalScales,rangeSize} from './structureScale';
import type {Panel} from './types';
const bars=Array.from({length:12},(_,i)=>({high:20+i,low:10+i}));
const panel={bars,fractals:[{id:'f0',source:1,kind:'bottom',price:11,basis_at:2,state:'closed_basis'},
 {id:'f1',source:5,kind:'top',price:25,basis_at:6,state:'closed_basis'},
 {id:'f2',source:8,kind:'bottom',price:18,basis_at:9,state:'closed_basis'}],
 strokes:[{id:'p0',start:1,end:5,direction:'up',state:'confirmed',basis_at:7}],
 segments:[{id:'s0',start:1,end:10,direction:'up',state:'provisional',basis_at:11}]} as unknown as Panel;
const points=fractalScales(panel);
assert.equal(points.length,3,'Every raw fractal stays visible');
assert.deepEqual(points.map(point=>point.scale),['segment','stroke','fractal']);
assert.equal(points[0].scale_state,'结构形成中');
assert.equal(points[0].size_confirmed_at_index,11,'Segment evidence cannot be backdated to the fractal');
assert.equal(points[0].price,11,'Classification preserves the raw price anchor');
assert.equal(points[0].range_bars,10);
assert.equal(points[1].range_high,25);assert.equal(points[1].range_low,11);
assert.equal(points[0].execution_allowed,false);
const center=rangeSize({start:1,end:5,zd:15,zg:18},bars);
assert.equal(center.core_height,3);assert.equal(center.core_width_percent,20);
assert.equal(center.range_amplitude_percent,(25-11)/11*100);
console.log('Fractal tiers preserve every price anchor, parent evidence time and exact range size.');
