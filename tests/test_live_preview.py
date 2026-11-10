import copy,unittest
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from chanmodel.model import Candle
from web import realtime_panel as live
from web.live_preview import changes
from tests.test_stroke_signals import market_bars

CN=timezone(timedelta(hours=8))


class LivePreviewTests(unittest.TestCase):
    def test_forming_price_changes_preview_without_changing_closed_model_or_confirmation(self):
        history=[replace(bar,open=round(bar.open,2),high=round(bar.high,2),low=round(bar.low,2),close=round(bar.close,2)) for bar in market_bars()[:100]]
        last=history[-1];stamp=datetime.fromisoformat(last.closed_at)+timedelta(days=1)
        forming=Candle(len(history),last.close,last.close+2,last.close-1,last.close+1,stamp.isoformat(),100,False)
        now=stamp.replace(hour=10);live.observations.clear()
        first=live.make_panel('sh600261','day',history+[forming],now)
        changed=replace(forming,high=forming.high+12,close=forming.close+8)
        second=live.make_panel('sh600261','day',history+[changed],now+timedelta(seconds=10))
        self.assertEqual(first['strokes'],second['strokes']);self.assertEqual(first['all_centers'],second['all_centers'])
        self.assertEqual(first['stroke_model']['signals'],second['stroke_model']['signals'])
        self.assertEqual(first['stroke_model']['confirmations'],[]);self.assertEqual(second['stroke_model']['confirmations'],[])
        self.assertNotEqual(first['update_revision'],second['update_revision'])
        self.assertNotEqual(first['live_preview']['input_sha256'],second['live_preview']['input_sha256'])
        self.assertEqual(first['coverage']['input_sha256'],second['coverage']['input_sha256'])
        self.assertFalse(second['bars'][-1]['is_closed'])
        self.assertFalse(second['provenance']['forming_bars_used_for_structure'])
        for model in [second['live_preview']['stroke'],second['live_preview']['segment']]:
            for items in model.values():
                for item in items:
                    self.assertTrue(item['live_preview']);self.assertEqual(item['state'],'live_preview')
                    self.assertIsNone(item['confirmed_at']);self.assertFalse(item['execution_allowed'])
        self.assertTrue(any(second['live_preview']['stroke'].values()))

    def test_no_forming_candle_produces_no_hypothetical_model(self):
        data=market_bars()[:40];now=datetime.fromisoformat(data[-1].closed_at)+timedelta(minutes=1)
        panel=live.make_panel('sh600261','day',data,now)
        self.assertIsNone(panel['live_preview'])

    def test_preview_cannot_mutate_or_confirm_the_stable_object(self):
        stable={'id':'p','state':'confirmed','start':0,'end':3,'end_price':10,'rule_audit':{'passed':True}}
        tentative={**stable,'end_price':12};before=copy.deepcopy(tentative)
        result=changes([tentative],[stable],datetime(2026,11,10,10,tzinfo=CN))
        self.assertEqual(tentative,before);self.assertEqual(stable['state'],'confirmed')
        self.assertEqual(len(result),1);self.assertFalse(result[0]['rule_audit']['passed'])
        self.assertEqual(changes([stable],[stable],datetime.now(CN)),[])

    def test_reusing_closed_structure_does_not_reuse_a_forming_price(self):
        data=market_bars()[:60];now=datetime.fromisoformat(data[-1].closed_at)+timedelta(minutes=1)
        live.structure_cache.clear()
        from chanmodel.complete_study import analyze_complete
        with patch('chanmodel.complete_study.analyze_complete',wraps=analyze_complete) as analyze:
            one=live.make_panel('sh600261','day',data,now,reuse_structure=True)
            two=live.make_panel('sh600261','day',data,now+timedelta(seconds=10),reuse_structure=True)
        self.assertEqual(analyze.call_count,1)
        self.assertNotEqual(one['fetched_at'],two['fetched_at'])
        self.assertEqual(one['signals'],two['signals'])


if __name__=='__main__':unittest.main()
