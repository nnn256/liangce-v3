"""Run the local research workstation on loopback, with isolated task storage."""
import argparse
import json
import os
from pathlib import Path
import threading
import time
from urllib.request import ProxyHandler,build_opener
import webbrowser

ROOT=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8830)
    parser.add_argument('--no-browser',action='store_true')
    options=parser.parse_args()
    origin=f'http://127.0.0.1:{options.port}'
    opener=build_opener(ProxyHandler({}))

    def probe():
        with opener.open(origin+'/api/research/health',timeout=2) as response:
            return json.load(response)

    try:
        running=probe()
    except OSError:
        running=None
    if running:
        if running.get('product')!='量测 v3' or running.get('hosting')!='local-research':
            raise SystemExit(f'Port {options.port} belongs to another service. Use --port to choose a free port.')
        print('Local workstation already running: '+origin,flush=True)
        if not options.no_browser:webbrowser.open(origin+'/?symbol=sz300949&period=5m')
        return

    os.chdir(ROOT)
    tdx_binary=ROOT/'.runtime/tdx-api-build/liangce-tdx.exe'
    if tdx_binary.is_file() and not os.environ.get('LIANGCE_TDX_API'):
        os.environ.setdefault('LIANGCE_TDX_BINARY',str(tdx_binary))
    os.environ.update(LIANGCE_HOSTING='local-research',LIANGCE_EPHEMERAL='0',
                      LIANGCE_ALLOWED_ORIGINS=origin,LIANGCE_RUNTIME=str(ROOT/'.runtime/local-research'),
                      LIANGCE_WORKERS='1',LIANGCE_QUEUE_LIMIT='2',LIANGCE_MAX_COMPUTE_BARS='30000',
                      LIANGCE_READONLY='0',STOCK_DATA_HOME=str(ROOT/'.runtime/local-market'))
    import uvicorn
    from web.research_server import app
    if not options.no_browser:
        def open_when_ready():
            for _ in range(30):
                try:
                    if probe().get('status')=='ok':
                        webbrowser.open(origin+'/?symbol=sz300949&period=5m');return
                except OSError:pass
                time.sleep(.5)
        threading.Thread(target=open_when_ready,daemon=True).start()
    print('Local research, signals and backtest: '+origin,flush=True)
    uvicorn.run(app,host='127.0.0.1',port=options.port,workers=1)


if __name__=='__main__':main()
