"""Offline API contracts and real archived evidence; no network fixtures."""
import gzip,hashlib,json,os,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'web'))
import research_api as api


class ResearchApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=FastAPI();cls.app.include_router(api.router);cls.client=TestClient(cls.app)

    def test_verified_symbol_map_keeps_exchange_and_name(self):
        d=self.client.get('/api/research/symbols',params={'q':'平安银行'}).json()
        self.assertEqual(d['results'][0]['symbol'],'sz000001')
        self.assertNotIn('上证',d['results'][0]['name'])
        self.assertEqual(self.client.get('/api/research/symbols',params={'q':'奥雅股份'}).json()['results'][0]['symbol'],'sz300949')

    def test_archive_data_integrity_and_confirmation_causality(self):
        d=self.client.get('/api/research/panel/300949.SZ/5m').json()
        self.assertEqual(d['source_kind'],'verified_historical_snapshot')
        self.assertEqual(d['coverage']['count'],23520)
        self.assertEqual(len(d['confirmations']),8)
        for e in d['confirmations']:
            self.assertLessEqual(e['anchor'],e['observed_index'])
            self.assertTrue(e['rule_audit']['passed'])
            self.assertFalse(e['execution_allowed'])

    def test_etag_conditional_get(self):
        r=self.client.get('/api/research/panel/sz300949/day')
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.get('/api/research/panel/sz300949/day',headers={'If-None-Match':r.headers['etag']}).status_code,304)

    def test_invalid_symbol_and_period_rejected(self):
        for code in ['../data','sz123','bad000001','sh300949']:
            self.assertEqual(self.client.get('/api/research/panel/'+code+'/day').status_code in [404,422],True)
        self.assertEqual(self.client.get('/api/research/panel/sz300949/banana').status_code,422)
        self.assertEqual(self.client.get('/api/research/panel/sz000001/1m').status_code,404)

    def test_post_validation_and_origin(self):
        self.assertEqual(self.client.post('/api/research/jobs',json={'symbol':'sz300949','cutoff':'2026-99-99'}).status_code,422)
        self.assertEqual(self.client.post('/api/research/jobs',json={},headers={'Origin':'https://unexpected.example'}).status_code,403)

    def test_readonly_and_token_controls(self):
        with patch.dict(os.environ,{'LIANGCE_READONLY':'1'}):
            self.assertFalse(self.client.get('/api/research/health').json()['compute_enabled'])
            self.assertEqual(self.client.post('/api/research/jobs',json={}).status_code,403)
        with patch.dict(os.environ,{'LIANGCE_API_TOKEN':'test-fixture-only'}):
            self.assertEqual(self.client.post('/api/research/jobs',json={}).status_code,401)

    def test_real_historical_prefix_job_removes_future_bars(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(api,'RUNTIME',Path(tmp)):
            payload=api.JobRequest(symbol='sz300949',period='day',source='archive',mode='backtest',cutoff='2022-01-10')
            ident='f'*32;api.jobs[ident]={'id':ident,'state':'queued','progress':0,'request':payload.model_dump()}
            api.build_dynamic(payload,ident)
            self.assertEqual(api.jobs[ident]['state'],'completed',api.jobs[ident])
            p=json.loads(gzip.decompress((Path(tmp)/'jobs'/ident/'panel.json.gz').read_bytes()))
            self.assertTrue(all(b['date_cn'][:10]<='2022-01-10' for b in p['bars']))
            self.assertLess(len(p['bars']),1381)
            self.assertFalse((Path(tmp)/'latest').exists())
            self.assertEqual(p['portfolio_metrics'],None)
            self.assertIn('本次重放',p['backtest_scope_note'])

    def test_timeshare_cannot_be_relabelled_as_ohlc(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(api,'RUNTIME',Path(tmp)):
            req=api.JobRequest(symbol='sz300949',period='timeshare',mode='backtest');ident='e'*32
            api.jobs[ident]={'id':ident,'state':'queued'};api.build_dynamic(req,ident)
            self.assertEqual(api.jobs[ident]['state'],'failed')
            self.assertIn('OHLC',api.jobs[ident]['error'])

    def test_manual_live_analysis_accepts_tdx_five_day_other_stock(self):
        from web import tdx_provider as tdx
        from chanmodel.model import Candle
        bars=[Candle(i,10,11,9,10,f'2026-01-{i+1:02}T15:00:00+08:00',10000,True) for i in range(6)]
        metadata={'source':'oficcejo/tdx-api','adjustment':'unadjusted'}
        with patch.object(tdx,'enabled',return_value=True),patch.object(tdx,'fetch',return_value=(bars,metadata)) as fetch:
            actual,provenance=api.live_bars('sh600825','5d')
        self.assertEqual(actual,bars);self.assertFalse(provenance['confirmation_eligible'])
        self.assertEqual(fetch.call_args.args[:2],('sh600825','5d'))

    def test_result_path_and_failed_job_are_not_success(self):
        self.assertEqual(self.client.get('/api/research/jobs/not-a-job/result').status_code,422)
        self.assertEqual(self.client.get('/api/research/jobs/'+'d'*32+'/result').status_code,404)


if __name__=='__main__':unittest.main()
