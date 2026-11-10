import copy,json,os,sys,tempfile,unittest
from datetime import datetime,timedelta
from pathlib import Path
from unittest.mock import Mock,patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'web'))
from web import auction_panel as auction,research_api as api,realtime_panel as live


def quote(stamp='20261110092000',price=56.3):
    return {'name':'奥雅股份','price':price,'prevClose':56.99,'quoteTime':stamp,
            'orderBook':{'bids':[{'price':56.3,'volume':100}],'asks':[{'price':56.31,'volume':120}]}}


class AuctionTests(unittest.TestCase):
    def test_only_observed_auction_points_are_recorded_and_duplicates_replace(self):
        now=datetime(2026,11,10,9,20,5,tzinfo=auction.CN)
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LIANGCE_RUNTIME':tmp}):
            first=auction.build('sz300949',quote(),now)
            second=auction.build('sz300949',quote(price=56.4),now+timedelta(seconds=1))
            self.assertEqual(first['auction']['samples'],1);self.assertEqual(second['auction']['samples'],1)
            self.assertEqual(second['points'][0]['value'],56.4)
            self.assertEqual(second['auction']['order_book']['bids'][0]['volume_lots'],100)
            self.assertEqual(second['signals'],[]);self.assertEqual(second['coverage']['closed_count'],0)
            self.assertFalse(second['provenance']['confirmation_eligible'])
            closing=auction.build('sz300949',quote('20261110161400'),now.replace(hour=16,minute=14))
            self.assertEqual(closing['auction']['samples'],1,'Continuous-session or postclose quotes cannot populate an auction curve')

    def test_stale_unknown_and_non_auction_data_never_create_auction_history(self):
        now=datetime(2026,11,10,9,20,tzinfo=auction.CN)
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LIANGCE_RUNTIME':tmp}):
            for data in [quote('20261109161400'),quote(None),quote('20261110093000')]:
                result=auction.build('sz300949',data,now)
                self.assertEqual(result['auction']['samples'],0)
                self.assertEqual(result['points'],[])
            self.assertFalse((Path(tmp)/'auction').exists())

    def test_final_auction_print_can_arrive_a_few_seconds_later(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LIANGCE_RUNTIME':tmp}):
            result=auction.build('sz300949',quote('20261110092500'),datetime(2026,11,10,9,25,4,tzinfo=auction.CN))
        self.assertEqual(result['auction']['samples'],1)
        self.assertEqual(auction.phase(datetime(2026,11,10,9,25,1)),'outside_auction')

    def test_live_auction_endpoint_uses_quote_source_without_kline_engine(self):
        app=FastAPI();app.include_router(api.router);client=TestClient(app);gateway=Mock()
        gateway.fetch_level1_quotes.return_value={'300949.SZ':quote('20261109161400')}
        auction.cache.clear()
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LIANGCE_RUNTIME':tmp}),patch.dict(sys.modules,{'market_gateway':gateway}):
            result=client.get('/api/research/live-panel/sz300949/auction?refresh=true')
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['source_kind'],'live_auction_snapshot')
        self.assertEqual(result.json()['signals'],[])
        self.assertEqual(result.headers['cache-control'],'no-store')
        gateway.fetch_symbol_klines.assert_not_called()

    def test_monitor_signal_endpoint_filters_payload_and_does_not_claim_replay(self):
        app=FastAPI();app.include_router(api.router);client=TestClient(app)
        point={'id':'p1','class':'third_buy','side':'buy','rank':0,'price':10,'event_time':'2026-11-10T10:00:00+08:00','state':'candidate'}
        model={'signals':[point],'confirmation_records':[{'id':'p1','state':'confirmed'}],
               'confirmations':[{'signal_id':'p1','confirmed_at':'2026-11-10T10:10:00+08:00','confirmation_semantics':'stroke_rule_current_observation'}]}
        panel={'stroke_model':model,'fetched_at':'2026-11-10T10:10:00+08:00','structure_as_of':'2026-11-10T10:10:00+08:00',
               'market_session':'trading_hours','provenance':{'source':'test'}}
        with patch.object(live,'live_panel',return_value=panel):
            result=client.get('/api/research/monitor-signals/sz300949/5m?resolution=stroke')
        self.assertEqual(result.status_code,200,result.text)
        self.assertTrue(result.json()['signals'][0]['confirmed'])
        self.assertEqual(result.json()['definition_mode'],'stroke_proxy')
        self.assertNotIn('bars',result.json())
        self.assertEqual(client.get('/api/research/monitor-signals/sz300949/auction').status_code,422)

    def test_stroke_current_confirmation_never_backdates_the_observation(self):
        from chanmodel.model import Candle
        bars=[Candle(i,10,11,9,10,f'2026-11-{i+2:02}T15:00:00+08:00',10000,True) for i in range(5)]
        point={'id':'test-current-stroke','class':'third_buy','side':'buy','rank':0,'price':9,'anchor':1,
               'event_time':bars[1].closed_at,'state':'candidate','rule_audit':{'passed':True}}
        now=datetime(2026,11,10,10,0,tzinfo=auction.CN)
        live.observations.clear()
        fine={'signals':[point],'strokes':[],'fractals':[],'centers':[]}
        with patch('chanmodel.stroke_signals.snapshot',side_effect=lambda closed:copy.deepcopy(fine)):
            first=live.make_panel('sz300949','day',bars,now)
            later=live.make_panel('sz300949','day',bars,now+timedelta(seconds=20))
        event=first['stroke_model']['confirmations'][0]
        self.assertEqual(event['confirmed_at'],now.isoformat())
        self.assertNotEqual(event['confirmed_at'],point['event_time'])
        self.assertIn('current_observation',event['confirmation_semantics'])
        self.assertEqual(later['stroke_model']['confirmations'][0]['confirmed_at'],event['confirmed_at'])


if __name__=='__main__':unittest.main()
