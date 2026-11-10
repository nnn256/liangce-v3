"""Exercise real hosted routes with full saved history under a container cap.

CI: docker run --memory=512m --memory-swap=512m --entrypoint python \
  -v "$PWD/scripts:/checks:ro" liangce-hosted /checks/stress_hosted_memory.py
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime,timedelta
import gzip,json,os,sys,threading,time
from pathlib import Path
from unittest.mock import patch

ROOT=Path.cwd();sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'web'))
from fastapi.testclient import TestClient
from chanmodel.model import Candle
from web.hosted_server import app
from web import tdx_provider as tdx
from web import realtime_panel as live
from web import workbench_api as workbench


def load(period):
    path=ROOT/'data/precision-replays/c91e98e2895a46e19aba467d5e593297'/(period+'.json.gz')
    saved=json.loads(gzip.decompress(path.read_bytes()))
    bars=[Candle(i,b['open'],b['high'],b['low'],b['close'],b['date_cn'].replace(' ','T')+':00+08:00',b['volume'],True) for i,b in enumerate(saved['chart_bars'])]
    last=bars[-1];stamp=datetime.fromisoformat(last.closed_at)+timedelta(days=1)
    bars.append(replace(last,pos=len(bars),closed_at=stamp.isoformat(),closed=False))
    return bars


def memory():
    if os.name!='nt':
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,2)
    import ctypes
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
    data=Counters();data.cb=ctypes.sizeof(data);ctypes.windll.kernel32.GetCurrentProcess.restype=ctypes.c_void_p
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_ulong]
    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(),ctypes.byref(data),data.cb)
    return round(data.PeakWorkingSetSize/1048576,2)


def main():
    histories={p:load(p) for p in ['day','5m','15m']};client=TestClient(app)
    labels=[]
    def fetch(code,period,now):
        time.sleep(.25)
        return histories[period],{'source':'exact_saved_market_ohlc_memory_test','adjustment':'unadjusted'}
    def query(code,period):
        response=client.get('/api/research/live-panel/'+code+'/'+period+'?refresh=true')
        if response.status_code==200:
            data=response.json();assert len(data['bars'])==len(histories[period]);assert data['live_preview']['not_confirmed']
            return {'status':200,'bars':len(data['bars']),'period':period}
        assert response.status_code==429,response.text
        return {'status':429,'period':period}
    with patch.object(tdx,'enabled',return_value=True),patch.object(tdx,'fetch',side_effect=fetch),patch.object(workbench,'fetch',side_effect=fetch):
        # Hold the actual shared budget with a large request; competitors must
        # fail promptly while health remains available, instead of accumulating.
        from web.compute_budget import status
        with ThreadPoolExecutor(max_workers=5) as pool:
            large=pool.submit(query,'sz301551','5m')
            deadline=time.monotonic()+10
            while status()['active'] is None and time.monotonic()<deadline:time.sleep(.01)
            competitors=[pool.submit(query,code,period) for code,period in [('sh600261','day'),('sz300949','15m'),('sh600825','5m')]]
            started=time.monotonic();health=client.get('/api/research/health');health_seconds=time.monotonic()-started
            assert health.status_code==200
            assert health_seconds<3,health_seconds
            labels.append(large.result())
            crowded=[future.result() for future in competitors]
            assert all(row['status']==429 for row in crowded),crowded
            labels+=crowded
        for code,period in [('sh600261','day'),('sz300949','15m'),('sz301551','5m'),('sh600825','day'),('sz301551','5m')]:
            labels.append(query(code,period))
        # The separately hosted workstation must share the same allocation
        # gate and retain only compressed state after its replay finishes.
        deadline=time.monotonic()+30;workbench_ready=False
        while time.monotonic()<deadline:
            response=client.get('/api/workbench/panel/sz301551/day')
            if response.status_code==200:
                state=response.json()['workbench_analysis']['status']
                if state=='ready':workbench_ready=True;break
                assert state in {'running','queued','updating'},response.text
            else:assert response.status_code==429,response.text
            time.sleep(.1)
        assert workbench_ready,'Workstation replay did not finish'
        from web.workbench_api import analysis
        assert all(isinstance(entry['session'],bytes) for entry in analysis.entries.values())
        labels.append(query('sz301551','5m'))
        assert client.get('/api/research/health').status_code==200
    peak=memory();assert peak<450,{'python_peak_mib':peak,'results':labels}
    assert live.structure_cache.bytes<=8*1024*1024
    assert all(isinstance(value,bytes) for value in live.structure_cache.items.values())
    print(json.dumps({'python_peak_mib':peak,'container_limit_mib':512,'health_seconds_while_busy':round(health_seconds,3),
                      'results':labels,'workbench_ready':workbench_ready,'compressed_model_cache_bytes':live.structure_cache.bytes,'status':'passed'}),flush=True)


if __name__=='__main__':main()
