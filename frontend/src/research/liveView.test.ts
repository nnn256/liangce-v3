import assert from 'node:assert/strict';
import {currentEvidence,withLivePreview} from './liveView';
import {displaySignals,signalStatus} from './signalDisplay';
import type {Panel} from './types';
const panel={source_kind:'live_market_panel',resolution:'stroke',coverage:{input_sha256:'closed'},fetched_at:'now',
 strokes:[{id:'p',state:'confirmed',end_price:10}],fractals:[],segments:[],all_centers:[],signals:[],confirmations:[],confirmation_records:[],
 live_preview:{stroke:{strokes:[{id:'p',state:'live_preview',live_preview:true,end_price:12}],signals:[{id:'s',class:'third_buy',side:'buy',rank:0,anchor:1,price:11,live_preview:true}]},segment:{}}} as unknown as Panel;
const changed=withLivePreview(panel)!;assert.equal(changed.strokes[0].end_price,12);
assert.equal(panel.strokes[0].end_price,10,'No modification of closed evidence');
assert.deepEqual(changed.confirmations,[]);assert.equal(changed.signals[0].has_confirmation,false);
assert.equal(signalStatus(displaySignals(changed)[0]),'实时预览 · 未收盘');
assert.equal(withLivePreview(panel,false),panel);
const saved={...panel,source_kind:'saved_causal_replay'};
assert.equal(withLivePreview(saved),saved,'A saved backtest is never replaced by a current preview');
const refreshed=currentEvidence({id:'p',end_price:9,navigation_key:'selection'},changed)!;
assert.equal(refreshed.end_price,12);assert.equal(refreshed.navigation_key,'selection');assert.equal(refreshed.live_checked_at,'now');
assert.equal(currentEvidence({id:'vanished',live_preview:true},changed)?.state,'preview_expired');
console.log('Live preview changes remain separate from confirmations, historical replay and selected evidence.');
