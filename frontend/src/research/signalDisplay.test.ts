import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {confirmationPlotIndex,displaySignals,signalStatus} from './signalDisplay';

const panel=JSON.parse(gunzipSync(readFileSync(new URL('../../public/research/sz300949__5m.json.gz',import.meta.url))).toString());
const signals=displaySignals(panel);
assert.equal(new Set(signals.map(point=>point.id)).size,signals.length);
assert.equal(signals.filter(point=>point.has_confirmation).length,8);
assert.equal(signals.filter(point=>point.class==='first_buy').length,1);
assert.equal(signals.filter(point=>point.class==='second_buy').length,0);
assert.equal(signals.filter(point=>point.class==='second_sell').length,1);
assert(signals.length>panel.signals.length,'Keep historical objects absent from the final structure');
const first=signals.find(point=>point.class==='first_buy')!;
assert.equal(signalStatus(first),'候选 · 已失效');
const confirmed=signals.find(point=>point.has_confirmation&&point.state==='invalidated')!;
assert.equal(signalStatus(confirmed),'历史确认 · 已失效');
assert(confirmed.confirmed_index>confirmed.anchor,'Price anchors must not be confused with the time confirmation became known');
assert.equal(signalStatus({has_confirmation:true,confirmation_semantics:'current_observation_only; earliest_historical_confirmation_not_claimed'}),'历史结构核对');
const old={signal_id:'old',class:'third_sell',rank:0,side:'sell',anchor:0,price:6.18,
 observed_index:2,observed_at:'2026-11-10T09:27:54+08:00',confirmation_semantics:'stroke_rule_current_observation; earliest_historical_confirmation_not_claimed',
 point:{id:'old',class:'third_sell',rank:0,side:'sell',anchor:0,price:6.18,event_time:'2017-10-27T15:00:00+08:00',available_time:'2017-11-07T15:00:00+08:00'}};
const axis=[{date_cn:'2017-10-27 15:00'},{date_cn:'2017-11-07 15:00'},{date_cn:'2026-11-09 15:00'}];
assert.equal(confirmationPlotIndex(old,axis),null,'A current check of an old structure cannot draw a confirmation at today');
const checked=displaySignals({...panel,bars:axis,signals:[old.point],signal_events:[],confirmation_records:[],confirmations:[old]})[0];
assert.equal(checked.snapshot_passed,true);assert.equal(checked.has_confirmation,undefined);
assert.equal(checked.observed_at,'2017-11-07T15:00:00+08:00');
assert.equal(signalStatus(checked),'历史结构核对');
const replay={...old,confirmation_semantics:'stroke_rule_prefix_observed',observed_at:'2017-11-07T15:00:00+08:00'};
assert.equal(confirmationPlotIndex(replay,axis),1,'Time mapping repairs stale numeric indices');
assert.equal(confirmationPlotIndex({...replay,observed_at:'2026-11-10T09:27:54+08:00'},axis),null,'An unavailable timestamp is never attached to a neighboring candle');
assert.equal(signalStatus({has_confirmation:true,snapshot_passed:true,confirmation_origin:'live_closed_bar_transition'}),'在线新增确认');
console.log('Real archive: historical signal reconciliation, confirmation timing and six-class counts passed.');
