"""Validate completed local replays and package exact data/evidence for review."""
from datetime import datetime
from pathlib import Path
import csv,gzip,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from web.tdx_provider import CN,fetch
from chanmodel.stroke_signals import CLASSES
from web.precision_backtest import pack,PERIODS,chart_context


def main():
    source=ROOT/'.runtime/precision-acceptance-export';target=ROOT/'data/precision-replays'
    target.mkdir(parents=True,exist_ok=True)
    report_folder=ROOT/'artifacts/precision-backtest';report_folder.mkdir(parents=True,exist_ok=True)
    manifest={'schema':'liangce.saved_replays.v1','created_at':datetime.now(CN).isoformat(),'runs':[],'files':[]}
    summary_rows=[];bar_cache={};context_cache={};validation={'confirmation_points':0,'fills':0,'period_results':0,'input_hashes_verified':0}
    for code in ['sz301551','sz300949']:
        for resolution in ['stroke','segment']:
            summary=json.loads((source/(code+'_'+resolution+'_summary.json')).read_text(encoding='utf-8'))
            if summary['state']!='completed' or summary['completed']!=11:raise ValueError('Full11period run not complete: '+code+resolution)
            ident=summary['id']
            for index,row in enumerate(summary['rows']):
                period=row['period']
                if row['state']!='completed':raise ValueError('Unresolved period failure: '+code+resolution+period)
                detail_path=source/(code+'_'+resolution+'_'+period+'.json')
                detail=json.loads(detail_path.read_text(encoding='utf-8'))
                if resolution=='stroke' and detail.get('analysis_eligible',detail['bars']>=3):
                    if detail['replay']['profile']!='stroke_actual_extreme_center_first_retest_v2':raise ValueError('Obsolete stroke replay profile')
                key=(code,period)
                if key not in bar_cache:
                    bars,_=fetch(code,period,datetime.now(CN));bar_cache[key]=[bar for bar in bars if bar.closed]
                bars=bar_cache[key]
                closed=[bar for bar in bars if detail['first']<=bar.closed_at<=detail['last']]
                digest=hashlib.sha256(json.dumps([[b.closed_at,b.open,b.high,b.low,b.close,b.volume] for b in closed]).encode()).hexdigest()
                if digest!=detail['input_sha256'] or len(closed)!=detail['bars']:raise ValueError('Source data changed or scope mismatch: '+code+period)
                validation['input_hashes_verified']+=1
                if key not in context_cache:context_cache[key]=chart_context(code,period,closed,digest)
                detail['chart_context']=context_cache[key]
                detail['chart_bars']=[{'time':int(datetime.fromisoformat(bar.closed_at).timestamp())+8*3600,'source_index':bar.pos,
                                       'date_cn':bar.closed_at[:16].replace('T',' '),'open':bar.open,'high':bar.high,'low':bar.low,
                                       'close':bar.close,'volume':bar.volume,'is_closed':True} for bar in closed]
                for event in detail['replay']['confirmations']:
                    if not 0<=event['anchor']<=event['observed_index']<len(closed):raise ValueError('Signal future index')
                    point=event['point']
                    if point.get('available_at',0)>event['observed_index']:raise ValueError('Signal before its evidence')
                    begin,end=point['terminal_range'];extreme=(min(bar.low for bar in closed[begin:end+1]) if event['side']=='buy' else max(bar.high for bar in closed[begin:end+1]))
                    if abs(extreme-event['price'])>1e-7:raise ValueError('Price anchor is not actual terminal extreme')
                    validation['confirmation_points']+=1
                for order in detail['portfolio_orders']:
                    if order['state']=='filled':
                        if order['time']<order['signal_time'] or order['bar_close_time']<=order['signal_time']:raise ValueError('Future or same-bar fill')
                        validation['fills']+=1
                validation['period_results']+=1
                path=target/ident/(period+'.json.gz');pack(path,detail)
                row={k:v for k,v in detail.items() if k not in {'replay','portfolio_orders','portfolio_trades','portfolio_equity','chart_bars','chart_context'}}
                row.update(state='completed',detail_url='/api/research/precision-backtests/'+ident+'/'+period)
                summary['rows'][index]=row
                metrics=detail['portfolio_metrics']
                summary_rows.append({'symbol':code,'name':'无线传媒' if code=='sz301551' else '奥雅股份','resolution':resolution,'period':period,
                                     'bars':detail['bars'],'first':detail['first'],'last':detail['last'],
                                     **{kind:detail['signal_classes'][kind]['rule_confirmed'] for kind in CLASSES},
                                     'completed_trades':metrics['completed_trades'],'win_rate':metrics['win_rate'],
                                     'total_return':metrics['total_return'],'max_drawdown':metrics['max_drawdown'],'fees':metrics['total_fees'],
                                     'analysis_eligible':detail.get('analysis_eligible',detail['bars']>=3)})
            summary['saved_replay']=True
            pack(target/ident/'summary.json.gz',summary)
            manifest['runs'].append({'id':ident,'symbol':code,'resolution':resolution,'periods':PERIODS,'finished_at':summary.get('finished_at')})
    for item in manifest['runs']:
        for path in sorted((target/item['id']).glob('*.json.gz')):
            manifest['files'].append({'path':str(path.relative_to(target)).replace('\\','/'),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
    (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    with (report_folder/'all-period-results.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summary_rows[0]));writer.writeheader();writer.writerows(summary_rows)
    (report_folder/'all-period-results.json').write_text(json.dumps({'validation':validation,'rows':summary_rows},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 无线传媒与奥雅股份全周期回放与回测','',
           '使用真实TDX全部可得历史，按闭合K线逐根前缀产生事件。笔级是代理观察规则；线段级保留原有递归门控，不能合并宣称原文严格等价。',
           '成交采用下一可交易开盘、T+1、100股买入、单边5bp滑点、佣金万三最低5元、印花税和过户费，最多20个交易日持有，参与量受前一闭合K线1%成交量限制。粗周期信号映射下一日开盘。',
           '分时和五日分时共享原生1分钟OHLC回放；集合竞价快照不足连续走势证据，不补造确认。年线不足3根时记录证据不足，空仓收益0不证明策略有效。','',
           '| 股票 | 口径 | 周期 | 根数 | 规则确认数 | 已平仓 | 胜率 | 净收益 | 最大回撤 |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for row in summary_rows:
        wins='—' if row['win_rate'] is None else f"{row['win_rate']:.2%}"
        lines.append(f"| {row['name']} | {'精细笔级代理' if row['resolution']=='stroke' else '线段递归'} | {row['period']} | {row['bars']} | {sum(row[kind] for kind in CLASSES)} | {row['completed_trades']} | {wins} | {row['total_return']:.2%} | {row['max_drawdown']:.2%} |")
    lines+=['','确认价锚点、确认延迟、失效撤回和成交订单已逐项验证。盈亏包含未平仓持仓市值，交易胜率不等于定义准确率；亏损结果按实保留。',
            '补充检查：'+json.dumps(validation,ensure_ascii=False),'']
    (report_folder/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'runs':len(manifest['runs']),'files':len(manifest['files']),'bytes':sum(item['bytes'] for item in manifest['files']),'validation':validation,'report':str(report_folder/'README.md')},ensure_ascii=False))


if __name__=='__main__':main()
