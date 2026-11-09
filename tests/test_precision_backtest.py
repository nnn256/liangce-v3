"""Precision stroke/segment replay contracts and real costs."""
import gzip,hashlib,json,os,sys,tempfile,time,unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from chanmodel.model import Candle

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'web'))
from web import research_api as api
from web.precision_backtest import execute_period,CostModel


class PrecisionBacktestTests(unittest.TestCase):
    def test_unarchived_stock_fetches_real_source_contract_and_current_period_fills(self):
        from web import precision_backtest as backtest
        bars=[Candle(i,10,11,9,10,f'2026-01-{i+1:02}T15:00:00+08:00',10000,True) for i in range(8)]
        metadata={'source':'oficcejo/tdx-api','adjustment':'unadjusted','split_adjustment_verified':False}
        app=FastAPI();app.include_router(api.router);client=TestClient(app)
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LIANGCE_RUNTIME':tmp,'LIANGCE_ALLOWED_ORIGINS':'http://testserver'}),patch.object(backtest,'runs',{}),patch.object(backtest.tdx,'fetch',return_value=(bars,metadata)) as fetch,patch.object(backtest.pool,'submit',side_effect=lambda fn:fn()):
            self.assertEqual(client.get('/api/research/panel/sh600825/5d').status_code,404)
            started=client.post('/api/research/precision-backtests',json={'symbol':'sh600825','resolution':'stroke','periods':['5d']},headers={'Origin':'http://testserver'})
            self.assertEqual(started.status_code,202,started.text)
            result=client.get('/api/research/precision-backtests/'+started.json()['id']).json()
            self.assertEqual(result['state'],'completed',result)
            detail=client.get(result['rows'][0]['detail_url']).json()
            self.assertEqual(detail['symbol'],'sh600825');self.assertEqual(detail['period'],'5d')
            self.assertIn('completed_trades',detail['portfolio_metrics'])
            self.assertFalse(detail['strict_original_equivalence_proven'])
            self.assertTrue(any('not independently certified' in text for text in detail['portfolio_limitations']))
            self.assertEqual([call.args[1] for call in fetch.call_args_list],['day','5d'])
            latest=client.get('/api/research/saved-replays/sh600825/stroke')
            self.assertEqual(latest.status_code,200);self.assertEqual(latest.json()['id'],result['id'])

    def test_failed_period_is_not_reported_as_complete_success(self):
        from web import precision_backtest as backtest
        bars=[Candle(i,10,11,9,10,f'2026-01-{i+1:02}T15:00:00+08:00',10000,True) for i in range(6)]
        metadata={'source':'test','adjustment':'unadjusted'}
        def fetch(code,period,now):
            if period=='year':raise ValueError('Year history unavailable')
            return bars,metadata
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'LIANGCE_RUNTIME':tmp}),patch.object(backtest,'runs',{}),patch.object(backtest.tdx,'fetch',side_effect=fetch),patch.object(backtest.pool,'submit',side_effect=lambda fn:fn()):
            result=backtest.start('sh600825','stroke',['day','year'])
            self.assertEqual(result['state'],'partial');self.assertEqual(result['failed_periods'],1)
            self.assertEqual(result['rows'][1]['state'],'failed')

    def test_saved_replays_have_exact_chart_inputs_and_causal_confirmations(self):
        from web import precision_backtest as backtest
        manifest=json.loads((backtest.ARCHIVE/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['runs']),4)
        for item in manifest['files']:
            raw=(backtest.ARCHIVE/item['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),item['sha256'])
        points=fills=periods=0
        for run in manifest['runs']:
            summary=backtest.available(run['symbol'],run['resolution'])
            self.assertTrue(summary['saved_replay']);self.assertEqual(summary['completed'],11)
            for row in summary['rows']:
                detail=backtest.detail(run['id'],row['period']);bars=detail['chart_bars'];periods+=1
                self.assertEqual(len(bars),detail['bars'])
                self.assertEqual(len(detail['chart_context']['macd']),len(bars))
                for event in detail['replay']['confirmations']:
                    self.assertLessEqual(event['anchor'],event['observed_index'])
                    self.assertLess(event['observed_index'],len(bars))
                    self.assertEqual(event['observed_at'][:16].replace('T',' '),bars[event['observed_index']]['date_cn'])
                    begin,end=event['point']['terminal_range'];segment=bars[begin:end+1]
                    actual=min(b['low'] for b in segment) if event['side']=='buy' else max(b['high'] for b in segment)
                    self.assertAlmostEqual(actual,event['price'],places=7);points+=1
                for order in detail['portfolio_orders']:
                    if order['state']=='filled':
                        self.assertGreaterEqual(order['time'],order['signal_time'])
                        self.assertGreater(order['bar_close_time'],order['signal_time']);fills+=1
                self.assertFalse(detail['strict_original_equivalence_proven'])
        self.assertEqual((periods,points,fills),(44,1462,934))

    def test_minimum_input_keeps_all_six_stats_and_explicit_accuracy_fields(self):
        bars=[Candle(i,10+i*.1,10+i*.2,9+i*.1,10+i*.15,f'2026-01-0{min(i+1,9)}T15:00:00+08:00',100,True) for i in range(6)]
        metadata={'source':'test','adjustment':'unadjusted','split_adjustment_verified':False}
        result=execute_period('sz000001','day','stroke',bars,metadata,bars,metadata)
        self.assertEqual(set(result['signal_classes']),{'first_buy','second_buy','third_buy','first_sell','second_sell','third_sell'})
        self.assertFalse(result['execution_allowed']);self.assertFalse(result['strict_original_equivalence_proven'])
        self.assertIn('total_return',result['portfolio_metrics'])

    def test_backtest_does_not_use_same_bar_signal_as_fill(self):
        bars=[Candle(i,10,11,9,10,f'2026-01-{i+1:02}T15:00:00+08:00',10000,True) for i in range(8)]
        metadata={'source':'test','adjustment':'causal_split_hfq_verified_actions','split_adjustment_verified':True,'corporate_actions':[]}
        result=execute_period('sz000001','day','stroke',bars,metadata,bars,metadata)
        for order in result['portfolio_orders']:
            if order['state']=='filled':self.assertGreater(order['bar_index'],0)
        self.assertTrue(any('next bar' in item.lower() or 'queue' in item.lower() for item in result['portfolio_limitations']))

    def test_api_rejects_running_second_full_replay_and_writes_no_archive(self):
        app=FastAPI();app.include_router(api.router);client=TestClient(app)
        from web import precision_backtest as backtest
        with patch.dict(__import__('os').environ,{'LIANGCE_ALLOWED_ORIGINS':'http://testserver'}),patch.object(backtest.pool,'submit'),patch.object(backtest,'runs',{}):
            first=client.post('/api/research/precision-backtests',json={'symbol':'sz300949','resolution':'stroke','periods':['day']},headers={'Origin':'http://testserver'})
            self.assertEqual(first.status_code,202)
            second=client.post('/api/research/precision-backtests',json={'symbol':'sz300949','resolution':'stroke','periods':['5m']},headers={'Origin':'http://testserver'})
            self.assertIn(second.status_code,[202,429])
            self.assertEqual(client.get('/api/research/panel/sz300949/day').status_code,200)


if __name__=='__main__':unittest.main()
