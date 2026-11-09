"""Fresh K lines, cache expiry, forming bars and immutable archive contracts."""
import copy
from datetime import datetime
import gzip,json,sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'web'))
from web import realtime_panel as live
from web import research_api as api


class RealtimePanelTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.include_router(api.router);self.client=TestClient(app)
        live.cache.clear();self.gateway=Mock()
        self.module=patch.dict(sys.modules,{'market_gateway':self.gateway});self.module.start()
        self.rows=[{'time':f'2026-11-{day:02}','open':20,'high':22,'low':19,'close':21,'volume':10} for day in range(2,7)]
        self.gateway.fetch_symbol_klines.return_value={'klines':copy.deepcopy(self.rows)}

    def tearDown(self):
        self.module.stop();live.cache.clear()

    def test_live_endpoint_fetches_fresh_provider_and_never_returns_archived_confirmation(self):
        response=self.client.get('/api/research/live-panel/sz300949/day')
        self.assertEqual(response.status_code,200,response.text)
        panel=response.json()
        self.assertEqual(panel['source_kind'],'live_market_panel')
        self.assertEqual(panel['confirmations'],[])
        self.assertFalse(panel['provenance']['confirmation_eligible'])
        self.assertFalse(panel['provenance']['forming_bars_used_for_structure'])
        self.assertEqual(response.headers['cache-control'],'no-store')
        self.gateway.fetch_symbol_klines.assert_called_once_with('300949.SZ','1D',refresh=True)

    def test_same_bar_price_is_refetched_after_cache_expiry(self):
        with patch.object(live.time,'monotonic',return_value=0):first=live.live_panel('sz300949','day')
        self.gateway.fetch_symbol_klines.return_value['klines'][-1]['close']=20.5
        with patch.object(live.time,'monotonic',return_value=1):cached=live.live_panel('sz300949','day')
        with patch.object(live.time,'monotonic',return_value=1000):changed=live.live_panel('sz300949','day')
        self.assertEqual(first['bars'][-1]['close'],21)
        self.assertEqual(cached['bars'][-1]['close'],21)
        self.assertEqual(changed['bars'][-1]['close'],20.5)
        self.assertEqual(self.gateway.fetch_symbol_klines.call_count,2)

    def test_unfinished_daily_high_does_not_enter_structural_signal_calculation(self):
        now=datetime(2026,11,9,10,0,tzinfo=live.CN)
        rows=self.rows+[{'time':'2026-11-09','open':21,'high':999,'low':20,'close':22,'volume':20}]
        candles=live.provider_bars(rows,'day',now)
        panel=live.make_panel('sz300949','day',candles,now)
        self.assertFalse(panel['bars'][-1]['is_closed'])
        self.assertEqual(panel['coverage']['forming_count'],1)
        self.assertEqual(panel['bars'][-1]['high'],999)
        self.assertEqual(panel['structure_as_of'],'2026-11-06T15:00:00+08:00')
        self.assertLessEqual(datetime.fromisoformat(panel['data_as_of']),now)
        self.assertTrue(all(point['source']<5 for point in panel['fractals']))
        self.assertEqual(panel['analysis_last_price'],21)

    def test_week_and_month_wait_for_period_end_not_provider_label_date(self):
        now=datetime(2026,11,9,20,0,tzinfo=live.CN)
        self.assertGreater(live.close_time('2026-11-09','week'),now)
        self.assertGreater(live.close_time('2026-11-09','month'),now)
        self.assertLess(live.close_time('2026-11-06','week'),now)
        self.assertEqual(live.close_time('2026-11-09','week').isoformat(),'2026-11-13T15:00:00+08:00')

    def test_current_minute_candle_is_visible_and_future_intervals_are_excluded(self):
        now=datetime(2026,11,9,10,2,tzinfo=live.CN)
        rows=[{**self.rows[0],'time':label} for label in ['2026-11-09 10:00','2026-11-09 10:05','2026-11-09 10:10']]
        bars=live.provider_bars(rows,'5m',now)
        self.assertEqual(len(bars),2);self.assertTrue(bars[0].closed);self.assertFalse(bars[1].closed)

    def test_unavailable_source_is_an_error_and_archive_remains_unchanged(self):
        archive=ROOT/'data/research/sz300949__day.json.gz';before=archive.read_bytes()
        self.gateway.fetch_symbol_klines.return_value={'klines':[]}
        self.assertEqual(self.client.get('/api/research/live-panel/sz300949/day').status_code,503)
        self.assertEqual(self.client.get('/api/research/live-panel/sz300949/auction').status_code,422)
        self.assertEqual(before,archive.read_bytes())
        self.assertEqual(json.loads(gzip.decompress(before))['data_as_of'][:10],'2026-11-06')


if __name__=='__main__':unittest.main()
