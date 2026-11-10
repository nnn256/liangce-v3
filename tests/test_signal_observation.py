"""First snapshot audits, incremental witnesses and stable exchange time."""
import copy,unittest
from datetime import datetime,timedelta,timezone
from chanmodel.model import Candle
from web import signal_observation as observation
from web.realtime_panel import make_panel
from unittest.mock import patch

CN=timezone(timedelta(hours=8))


def bars(count,start=0):
    return [Candle(i,10,11,9,10,datetime(2026,10,20+i+start,15,tzinfo=CN).isoformat(),10000,True) for i in range(count)]


def point(data,anchor=0,evidence=1):
    return {'id':'old-sell','class':'third_sell','side':'sell','rank':0,'anchor':anchor,'price':10.5,
            'event_time':data[anchor].closed_at,'available_at':evidence,'available_time':data[evidence].closed_at,
            'terminal_range':[anchor,anchor+1],'invalidation':12,'zd':12,'zg':13,'state':'candidate','rule_audit':{'passed':True}}


class SignalObservationTests(unittest.TestCase):
    def setUp(self):observation.sessions.clear();self.now=datetime(2026,10,25,16,tzinfo=CN)

    def test_first_snapshot_of_old_signal_is_audit_without_new_confirmation(self):
        data=bars(5);p=point(data)
        records,events=observation.observe('sh600261','day','stroke',[p],data,self.now)
        self.assertEqual(events,[])
        self.assertEqual(records[0]['state'],'snapshot_validated')
        self.assertEqual(records[0]['evidence_at'],data[1].closed_at)
        self.assertEqual(records[0]['audited_at'],self.now.isoformat())
        self.assertNotIn('confirmed_at',records[0])

    def test_rechecking_same_bars_cannot_create_a_new_witness(self):
        data=bars(5);p=point(data,evidence=4)
        observation.observe('sh600261','day','stroke',[p],data,self.now)
        _,events=observation.observe('sh600261','day','stroke',[p],data,self.now+timedelta(hours=1))
        self.assertEqual(events,[])

    def test_only_new_closed_bar_evidence_can_be_witnessed(self):
        data=bars(6)
        observation.observe('sh600261','day','stroke',[],data[:5],self.now)
        p=point(data,evidence=5)
        records,events=observation.observe('sh600261','day','stroke',[p],data,self.now+timedelta(minutes=1))
        self.assertEqual(len(events),1)
        self.assertEqual(records[0]['state'],'confirmed')
        self.assertEqual(events[0]['observed_index'],5)
        self.assertEqual(events[0]['evidence_at'],data[5].closed_at)
        self.assertEqual(events[0]['confirmation_origin'],'live_closed_bar_transition')
        self.assertFalse(events[0]['historical_first_confirmation_verified'])

    def test_old_geometry_reappearing_after_new_bar_does_not_become_current_signal(self):
        data=bars(6)
        observation.observe('sh600261','day','stroke',[],data[:5],self.now)
        records,events=observation.observe('sh600261','day','stroke',[point(data,evidence=1)],data,self.now)
        self.assertEqual(events,[]);self.assertEqual(records[0]['state'],'snapshot_validated')

    def test_sliding_window_remaps_witness_by_time_without_moving_price_anchor(self):
        data=bars(6);p=point(data,anchor=2,evidence=5)
        observation.observe('sh600261','day','stroke',[],data[:5],self.now)
        _,original=observation.observe('sh600261','day','stroke',[p],data,self.now)
        moved=[Candle(i,b.open,b.high,b.low,b.close,b.closed_at,b.volume,b.closed) for i,b in enumerate(data[1:])]
        changed={**p,'id':'slid','anchor':1,'available_at':4,'terminal_range':[1,2]}
        _,events=observation.observe('sh600261','day','stroke',[changed],moved,self.now+timedelta(seconds=15))
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['observed_index'],4)
        self.assertEqual(events[0]['evidence_at'],original[0]['evidence_at'])
        self.assertEqual(events[0]['anchor_time'],original[0]['anchor_time'])
        self.assertEqual(events[0]['confirmed_at'],original[0]['confirmed_at'])

    def test_baseline_audit_is_used_for_both_stroke_and_segment_modes(self):
        data=bars(5);p=point(data)
        with patch('chanmodel.stroke_signals.snapshot',return_value={'signals':[p],'strokes':[],'centers':[],'fractals':[]}):
            panel=make_panel('sh600261','day',data,self.now)
        self.assertEqual(panel['stroke_model']['confirmations'],[])
        self.assertEqual(panel['stroke_model']['confirmation_records'][0]['state'],'snapshot_validated')

    def test_online_confirmation_is_withdrawn_if_its_structural_gate_no_longer_passes(self):
        data=bars(6);p=point(data,evidence=5)
        observation.observe('sh600261','day','stroke',[],data[:5],self.now)
        _,events=observation.observe('sh600261','day','stroke',[p],data,self.now)
        self.assertEqual(len(events),1)
        changed={**p,'rule_audit':{'passed':False}}
        records,events=observation.observe('sh600261','day','stroke',[changed],data,self.now+timedelta(seconds=15))
        self.assertEqual(events,[]);self.assertEqual(records[0]['state'],'withdrawn')


if __name__=='__main__':unittest.main()
