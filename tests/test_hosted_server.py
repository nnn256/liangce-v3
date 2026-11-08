"""Hosted entry boots with minimal dependencies and serves real evidence."""
import gzip,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from web import hosted_server as host
from web import research_api as api


class HostedServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.client=TestClient(host.app)

    def test_health_needs_no_scientific_or_legacy_market_boot(self):
        source='''import json,sys
from web.hosted_server import app
from web.research_api import health
health()
print(json.dumps({name:name in sys.modules for name in ['numpy','pandas','akshare','mootdx','main','market_gateway']}))
'''
        p=subprocess.run([sys.executable,'-c',source],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertFalse(any(json.loads(p.stdout).values()))

    def test_github_pages_cors_preflight_and_actual_response(self):
        origin='https://nnn256.github.io'
        headers={'Origin':origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}
        response=self.client.options('/api/research/jobs',headers=headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['access-control-allow-origin'],origin)
        response=self.client.get('/api/research/health',headers={'Origin':origin})
        self.assertEqual(response.headers['access-control-allow-origin'],origin)
        denied=self.client.options('/api/research/jobs',headers={**headers,'Origin':'https://unexpected.example'})
        self.assertEqual(denied.status_code,400)

    def test_static_frontend_and_real_research_gzip_are_available(self):
        r=self.client.get('/');self.assertEqual(r.status_code,200);self.assertIn('量测 v3',r.text)
        r=self.client.get('/research/sz300949__day.json.gz');self.assertEqual(r.status_code,200)
        data=json.loads(gzip.decompress(r.content));self.assertEqual(len(data['bars']),1381)
        self.assertEqual(self.client.get('/api/paper/reset').status_code,404)

    def test_resource_caps_and_ephemeral_storage_are_honest(self):
        with patch.dict(os.environ,{'LIANGCE_HOSTING':'render-free','LIANGCE_EPHEMERAL':'1'}):
            info=self.client.get('/api/research/health').json()
        self.assertEqual(info['hosting'],'render-free');self.assertEqual(info['runtime_storage'],'ephemeral')
        self.assertEqual(info['compute_limits']['max_input_bars'],api.MAX_COMPUTE_BARS)

    def test_compute_limit_fails_explicitly_instead_of_truncating_history(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(api,'RUNTIME',Path(tmp)),patch.object(api,'MAX_COMPUTE_BARS',100):
            req=api.JobRequest(period='day',source='archive',mode='analysis');ident='b'*32
            api.jobs[ident]={'id':ident,'state':'queued'}
            api.build_dynamic(req,ident)
            self.assertEqual(api.jobs[ident]['state'],'failed')
            self.assertIn('100根',api.jobs[ident]['error'])
            self.assertFalse((Path(tmp)/'jobs'/ident/'panel.json.gz').exists())

    def test_bounded_job_executes_against_actual_historical_prefix(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(api,'RUNTIME',Path(tmp)):
            req=api.JobRequest(period='day',mode='backtest',cutoff='2022-01-10');ident='a'*32
            api.jobs[ident]={'id':ident,'state':'queued'};api.build_dynamic(req,ident)
            self.assertEqual(api.jobs[ident]['state'],'completed',api.jobs[ident])
            data=json.loads(gzip.decompress((Path(tmp)/'jobs'/ident/'panel.json.gz').read_bytes()))
            self.assertTrue(all(x['date_cn'][:10]<='2022-01-10' for x in data['bars']))
            self.assertFalse(data['execution_allowed'])


if __name__=='__main__':unittest.main()
