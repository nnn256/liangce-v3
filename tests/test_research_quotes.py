"""Batch quote contracts: true symbols, zero/missing returns, cache and failures."""
import sys,time,unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock,patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'web'))
import research_api as api


class ResearchQuotesTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI();app.include_router(api.router);self.client=TestClient(app)
        api.quote_cache.clear()
        self.gateway=Mock()
        self.module=patch.dict(sys.modules,{'market_gateway':self.gateway});self.module.start()

    def tearDown(self):
        self.module.stop();api.quote_cache.clear()

    def test_batch_normalizes_symbols_and_preserves_source_market_time(self):
        self.gateway.fetch_level1_quotes.return_value={
            '300949.SZ':{'name':'奥雅股份','price':56.99,'prevClose':50.65,'changePercent':12.52,'quoteTime':'20261106161430'},
            '000001.SZ':{'name':'平安银行','price':11.81,'prevClose':11.64,'changePercent':1.46}}
        response=self.client.get('/api/research/quotes',params={'symbols':'300949.SZ,sz000001,sz300949'})
        self.assertEqual(response.status_code,200)
        data=response.json();self.assertEqual(data['missing'],[])
        self.assertEqual(data['quotes']['sz300949']['market_time'],'2026-11-06T16:14:30+08:00')
        self.assertIsNone(data['quotes']['sz000001']['market_time'])
        self.gateway.fetch_level1_quotes.assert_called_once_with(['300949.SZ','000001.SZ'])

    def test_unchanged_price_is_zero_and_missing_previous_close_is_unknown(self):
        self.gateway.fetch_level1_quotes.return_value={
            '000001.SZ':{'price':12,'prevClose':12,'changePercent':0},
            '600519.SH':{'price':1500,'changePercent':0}}
        data=self.client.get('/api/research/quotes',params={'symbols':'sz000001,sh600519'}).json()['quotes']
        self.assertEqual(data['sz000001']['change_percent'],0)
        self.assertIsNone(data['sh600519']['change_percent'])

    def test_cached_rows_are_reused_and_new_symbol_fetches_only_missing(self):
        self.gateway.fetch_level1_quotes.side_effect=[{'000001.SZ':{'price':12,'prevClose':11}},
                                                    {'600519.SH':{'price':1500,'prevClose':1510}}]
        for symbols in ['sz000001','sz000001','sz000001,sh600519']:
            self.assertEqual(self.client.get('/api/research/quotes',params={'symbols':symbols}).status_code,200)
        self.assertEqual(self.gateway.fetch_level1_quotes.call_count,2)
        self.assertEqual(self.gateway.fetch_level1_quotes.call_args.args[0],['600519.SH'])

    def test_failed_source_marks_old_quote_stale_and_does_not_make_up_missing(self):
        api.quote_cache['sz000001']=(time.monotonic()-3600,{'price':12,'change_percent':1,'symbol':'sz000001'})
        self.gateway.fetch_level1_quotes.return_value={}
        data=self.client.get('/api/research/quotes',params={'symbols':'sz000001,sh600519'}).json()
        self.assertTrue(data['quotes']['sz000001']['stale'])
        self.assertEqual(data['missing'],['sh600519']);self.assertIsNotNone(data['error'])
        api.quote_cache.clear()
        self.assertEqual(self.client.get('/api/research/quotes',params={'symbols':'sz000001'}).status_code,503)

    def test_bad_symbols_and_oversized_batches_never_reach_upstream(self):
        for symbols in ['', 'sh300949', '../file', ','.join(['sz000001']*81)]:
            self.assertEqual(self.client.get('/api/research/quotes',params={'symbols':symbols}).status_code,422)
        self.gateway.fetch_level1_quotes.assert_not_called()

    def test_refresh_interval_changes_for_session_and_weekend(self):
        self.assertTrue(api.quote_session(datetime(2026,11,9,10,0)))
        for value in [datetime(2026,11,8,10,0),datetime(2026,11,9,12,0),datetime(2026,11,9,16,0)]:
            self.assertFalse(api.quote_session(value))


if __name__=='__main__':unittest.main()
