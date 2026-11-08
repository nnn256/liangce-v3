"""Responsive acceptance through the installed agent-browser native CLI.

Checks real production pages and interactions; no browser-framework dependency.
"""
import argparse,base64,json,os,shutil,subprocess,time,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/qa'
CLI=shutil.which('agent-browser')
if CLI and CLI.lower().endswith(('.cmd','.bat')):
    native=Path(CLI).parent/'node_modules/agent-browser/bin/agent-browser-win32-x64.exe'
    if native.exists():CLI=str(native)


def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8810');parser.add_argument('--static',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);session='liangce-acceptance-'+('static' if args.static else 'api')
    results=[]
    def command(*parts):
        # Windows browser daemons may inherit stdout. File handles avoid an
        # EOF wait on a pipe kept alive by the long-running browser process.
        with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as error:
            p=subprocess.run([CLI,'--session',session,*map(str,parts)],stdout=output,stderr=error,timeout=65)
            output.seek(0);error.seek(0);stdout=output.read().decode('utf-8',errors='replace');stderr=error.read().decode('utf-8',errors='replace')
        if p.returncode:raise RuntimeError(stdout+stderr)
        return stdout
    def js(source):
        code='JSON.stringify((()=>{'+source+'})())';raw=command('eval','-b',base64.b64encode(code.encode()).decode())
        result=json.loads(raw)
        return json.loads(result) if isinstance(result,str) else result
    def check(name,source,expected=True):
        value=js(source);passed=value==expected
        results.append({'check':name,'passed':passed,'value':value})
        print(name,'PASS' if passed else 'FAIL',flush=True)
        if not passed:raise AssertionError(name+': '+str(value))
    def click(name):
        command('find','role','button','click','--name',name,'--exact')
    def wait_chart():command('wait','--fn','document.querySelector("[data-chart-ready=true]") !== null')
    def fill_date(value):
        # agent-browser 0.34 reports success for type=date but leaves it empty.
        # Dispatch native value/input/change through the actual form element.
        return js('const e=document.querySelector("input[aria-label=历史截止日期]");Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(e,'+json.dumps(value)+');e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}));return e.value')
    try:
        for name,w,h in [('desktop',1440,900),('laptop',1280,720),('tablet',768,1024),('mobile',390,844)]:
            command('set','viewport',w,h);command('open',args.url);wait_chart()
            check(name+'_no_horizontal_overflow','return document.documentElement.scrollWidth<=innerWidth+1')
            check(name+'_real_canvas','return document.querySelectorAll("canvas").length>=6')
            if name=='mobile':check('mobile_chart_visible_first_screen','return document.querySelector(".lc-main-chart").getBoundingClientRect().top<innerHeight-180')
            command('screenshot',OUT/(name+('-static' if args.static else '')+'.png'))
        # Mobile navigation, stock drawer, market identity and error recovery.
        click('自选');check('mobile_stock_drawer','return document.querySelector(".lc-watchlist").classList.contains("drawer-open")')
        command('fill','input[aria-label="搜索股票代码或名称"]','平安银行');command('wait','.lc-search-results button')
        command('click','.lc-search-results button');command('wait','--text','当前研究尚未就绪')
        check('no_fabricated_other_stock_snapshot','return document.body.innerText.includes("平安银行")&&document.body.innerText.includes("当前研究尚未就绪")')
        click('自选');command('click','.lc-stock-row:first-child');wait_chart()
        command('find','role','tab','click','--name','日K','--exact');wait_chart()
        check('period_url_and_real_dataset','return new URL(location.href).searchParams.get("period")==="day"&&document.querySelector(".lc-metrics").innerText.includes("1,381")')
        click('a/b/c/d');click('原文分解');check('both_abcd_selectors_available','return document.querySelectorAll(".lc-abcd-controls select").length===2')
        command('find','role','tab','click','--name','5分','--exact');wait_chart()
        click('回测');check('mobile_backtest_available','return document.body.innerText.includes("真实确认，再进入回测")&&document.querySelectorAll(".lc-backtest-page table tbody tr").length>0')
        click('看盘');wait_chart()
        # Test settings errors via actual user form then restore default.
        click('设置');command('fill','input[aria-label="后端地址"]','ftp://invalid.example');click('保存并检查');command('wait','--text','只支持HTTP或HTTPS后端地址')
        check('invalid_backend_validation','return document.querySelector(".lc-connection-result").innerText.includes("只支持HTTP或HTTPS")')
        click('关闭对话框');
        command('set','viewport',1440,900);command('open',args.url);wait_chart()
        command('click','.signal-table tbody tr:first-child');
        check('confirmed_evidence_gates_open','return document.querySelector(".lc-audit-gates")!==null')
        command('screenshot',OUT/('confirmed-evidence'+('-static' if args.static else '')+'.png'))
        # This headless Windows runtime cancels every browser download, even
        # a one-line data:text/plain link. Intercept only the final anchor click
        # and validate the exact PNG the real export action generated.
        js('window.__qaAnchorClick=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){if(this.download){window.__qaExport={name:this.download,url:this.href};return}return window.__qaAnchorClick.call(this)};return true')
        click('导出PNG');command('wait','--fn','Boolean(window.__qaExport?.url?.startsWith("data:image/png;base64,"))')
        export=js('return window.__qaExport')
        png=base64.b64decode(export['url'].split(',',1)[1]);path=OUT/('chart-export'+('-static' if args.static else '')+'.png');path.write_bytes(png)
        if not png.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Export is not a PNG')
        results.append({'check':'export_action_generates_downloadable_png','passed':True,'file':path.name,'bytes':len(png),'download_filename':export['name'],'native_download_runtime':'Headless runtime cancels even plain-text downloads; final anchor intercepted for validation'})
        js('HTMLAnchorElement.prototype.click=window.__qaAnchorClick;return true')
        if not args.static:
            click('新建研究');fill_date('2022-01-10');
            # Use daily data for a quick, meaningful real prefix computation.
            click('关闭对话框');command('find','role','tab','click','--name','日K','--exact');wait_chart();click('新建研究');fill_date('2022-01-10')
            check('historical_cutoff_input','return document.querySelector("input[aria-label=历史截止日期]").value==="2022-01-10"')
            click('开始计算')
            command('wait','--fn','document.querySelector(".lc-job-strip")?.innerText.includes("100%") === true')
            check('historical_prefix_job_completed','return document.body.innerText.includes("历史截止 2022-01-10")&&!document.querySelector(".lc-job-strip.failed")')
        # Meaningful diagnostics rather than relying only on generated screenshots.
        console=command('errors','--json')
        console_data=json.loads(console)
        if console_data.get('data',{}).get('errors'):raise AssertionError('Browser JavaScript errors: '+console)
        (OUT/('console-'+('static' if args.static else 'api')+'.json')).write_text(console,encoding='utf-8')
        report={'status':'pass','url':args.url,'mode':'static' if args.static else 'api','checks':results,'screenshots':['desktop.png','laptop.png','tablet.png','mobile.png'],'console':console}
    except Exception as exc:
        report={'status':'fail','url':args.url,'mode':'static' if args.static else 'api','checks':results,'error':str(exc)}
        try:command('screenshot',OUT/'failure.png','--full')
        except Exception:pass
    finally:
        path=OUT/('acceptance-'+('static' if args.static else 'api')+'.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2))
        command('close')
    return report['status']!='pass'


if __name__=='__main__':raise SystemExit(main())
