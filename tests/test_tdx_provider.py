"""Documented TDX REST units, full-period mapping and split-safe aggregation."""
from datetime import datetime
import unittest
from unittest.mock import patch
import time
from chanmodel.model import Candle
from web import tdx_provider as tdx
from web.realtime_panel import make_panel
from web import realtime_panel as live


def row(date,price=10000,volume=10):
    return {'Time':date,'Open':price,'High':price+1000,'Low':price-1000,'Close':price,'Volume':volume,'Amount':0}


class TdxProviderTests(unittest.TestCase):
    def setUp(self):self.now=datetime(2026,11,9,20,0,tzinfo=tdx.CN)

    def test_exact_protocol_units_sorted_rows_and_source_metadata(self):
        data={'count':2,'list':[row('2026-11-09T15:00:00+08:00',56300),row('2026-11-06T15:00:00+08:00',56990)],'meta':{'source':'tdx','type':'day'}}
        bars,meta=tdx.normalize_rest(data,'day',self.now)
        self.assertEqual([bar.close for bar in bars],[56.99,56.3])
        self.assertEqual(bars[0].volume,1000)
        self.assertEqual(meta['scope'],'all_provider_native_pages')
        self.assertEqual(meta['source_price_unit'],'milli_CNY')
        self.assertFalse(meta['source_retention_unlimited'])

    def test_count_period_or_duplicate_conflicts_are_errors(self):
        cases=[{'count':2,'list':[row('2026-11-09')]},
               {'list':[row('2026-11-09')],'meta':{'source':'ths','type':'day'}},
               {'list':[row('2026-11-09')],'meta':{'source':'tdx','type':'month'}},
               {'list':[row('2026-11-09'),row('2026-11-09',20000)]}]
        for data in cases:
            with self.assertRaises(ValueError):tdx.normalize_rest(data,'day',self.now)

    def test_minute_close_grid_and_zero_activity_marker_are_explicit(self):
        marker={'Time':'2026-11-09T13:00:00+08:00','Open':10000,'High':10000,'Low':10000,'Close':10000,'Volume':0,'Amount':0}
        data={'list':[marker,row('2026-11-09T13:05:00+08:00')]}
        bars,meta=tdx.normalize_rest(data,'5m',self.now)
        self.assertEqual(len(bars),1);self.assertEqual(meta['quarantined_zero_activity_rows'],1)
        with self.assertRaises(ValueError):tdx.normalize_rest({'list':[row('2026-11-09T13:01:00+08:00')]},'5m',self.now)

    def test_preopen_scheduled_flat_zero_activity_bucket_is_not_a_future_trade(self):
        now=datetime(2026,11,10,9,12,tzinfo=tdx.CN)
        previous=row('2026-11-09T15:00:00+08:00',56300)
        placeholder={'Time':'2026-11-10T09:35:00+08:00','Open':56300,'High':56300,'Low':56300,'Close':56300,'Volume':0,'Amount':0}
        bars,meta=tdx.normalize_rest({'list':[previous,placeholder]},'5m',now)
        self.assertEqual(len(bars),1);self.assertEqual(meta['quarantined_preopen_placeholders'],1)
        self.assertEqual(bars[0].closed_at,previous['Time'])
        with self.assertRaises(ValueError):tdx.normalize_rest({'list':[{**placeholder,'Volume':10}]},'5m',now)
        with self.assertRaises(ValueError):tdx.normalize_rest({'list':[{**placeholder,'Time':'2026-11-10T10:00:00+08:00'}]},'5m',now)

    def test_cross_split_calendar_aggregation_uses_adjusted_daily_ohlc(self):
        bars=[Candle(0,100,110,90,100,'2026-05-28T15:00:00+08:00',100),
              Candle(1,70,72,68,70,'2026-05-29T15:00:00+08:00',145)]
        adjusted,meta=tdx.split_adjust('sz300949',bars,{'source':'tdx'})
        self.assertEqual(adjusted[1].close,101.5)
        month=tdx.calendar_bars(adjusted,'month',self.now)
        self.assertEqual(len(month),1)
        self.assertEqual(month[0].high,110)
        self.assertEqual(month[0].low,90)
        self.assertEqual(month[0].close,101.5)
        self.assertEqual(meta['raw_last_price'],70)
        self.assertTrue(meta['split_adjustment_verified'])

    def test_five_day_tail_is_not_misrepresented_as_a_closed_five_day_bar(self):
        bars=[Candle(i,10,11,9,10,f'2026-11-{i+1:02}T15:00:00+08:00',100) for i in range(7)]
        grouped=tdx.five_day_bars(bars)
        self.assertEqual(len(grouped),2);self.assertTrue(grouped[0].closed);self.assertFalse(grouped[1].closed)
        self.assertEqual(grouped[0].volume,500)

    def test_all_native_kline_periods_map_to_exact_api_types(self):
        self.assertEqual(set(tdx.PERIODS),{'1m','5m','15m','30m','60m','day','5d','week','month','quarter','year'})
        self.assertEqual(tdx.PERIODS['1m'],'minute1');self.assertEqual(tdx.PERIODS['60m'],'hour')
        self.assertGreater(tdx.period_end('2026-11-09','quarter'),self.now)
        self.assertGreater(tdx.period_end('2026-11-09','year'),self.now)
        with self.assertRaises(ValueError):tdx.fetch('sz300949','auction',self.now)

    def test_yearly_source_with_six_bars_does_not_invent_any_trade_label(self):
        rows=[row(f'{year}-12-31',10000+(year-2020)*1000) for year in range(2021,2026)]
        bars,meta=tdx.normalize_rest({'list':rows},'year',self.now)
        panel=make_panel('sz300949','year',bars,self.now,meta)
        self.assertEqual(panel['signals'],[]);self.assertEqual(panel['confirmations'],[])
        self.assertEqual(len(panel['signal_diagnostics']),6)
        self.assertTrue(all(item['bars']==5 for item in panel['signal_diagnostics'].values()))

    def test_all_period_scan_preserves_individual_failure_and_six_classes(self):
        def panel(code,period):
            if period=='year':raise ValueError('insufficient historical bars')
            return {'coverage':{'count':100,'closed_count':99,'last':'2026-11-09 15:00'},
                    'provenance':{'source':'tdx'},'signal_diagnostics':{kind:{'candidates':1,'confirmed':0} for kind in ['first_buy','second_buy','third_buy','first_sell','second_sell','third_sell']}}
        live.scans.clear()
        with patch.object(live,'live_panel',side_effect=panel):
            live.period_overview('sz300949')
            deadline=time.monotonic()+3
            while live.scans['sz300949']['state']!='completed' and time.monotonic()<deadline:time.sleep(.01)
            result=live.period_overview('sz300949')
        self.assertEqual(result['completed'],11)
        self.assertEqual(result['rows'][-1]['state'],'failed')
        self.assertIn('insufficient historical bars',result['rows'][-1]['error'])
        self.assertEqual(len(result['rows'][0]['signals']),6)
        live.scans.clear()


if __name__=='__main__':unittest.main()
