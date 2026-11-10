"""Offline reproduction of a suspect live confirmation against exact saved bars.

Example: python scripts/audit_signal_observation.py --source artifacts/local-signal-audit/source.json
"""
import argparse,json,sys
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from chanmodel.model import Candle
from chanmodel.stroke_signals import replay,snapshot
from web.realtime_panel import make_panel,observations


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--signal',default='ps:third_sell:pc:4022:4041:4136')
    parser.add_argument('--symbol',default='sh600261')
    parser.add_argument('--period',default='day')
    args=parser.parse_args()
    saved=json.loads(args.source.read_text(encoding='utf-8'));bars=[Candle(**row) for row in saved['bars']]
    closed=[bar for bar in bars if bar.closed];now=datetime.fromisoformat(saved['now'])
    result=replay(closed,args.period)
    events=[event for event in result['confirmations'] if event['signal_id']==args.signal]
    if len(events)!=1:raise ValueError('Expected exactly one prefix confirmation for the selected signal')
    event=events[0];point=event['point'];at=event['observed_index']
    previous=snapshot(closed[:at])['signals'];current=snapshot(closed[:at+1])['signals']
    assert not any(item['id']==args.signal for item in previous)
    assert any(item['id']==args.signal and item['rule_audit']['passed'] for item in current)
    observations.clear();panel=make_panel(args.symbol,args.period,bars,now,saved['meta'])
    fine=panel['stroke_model'];record=next(record for record in fine['confirmation_records'] if record['id']==args.signal)
    assert record['state']=='snapshot_validated'
    assert not any(item['signal_id']==args.signal for item in fine['confirmations'])
    assert record['evidence_at']==event['observed_at']
    summary={'symbol':args.symbol,'period':args.period,'signal_id':args.signal,'closed_bars':len(closed),
             'forming_bars':len(bars)-len(closed),'source':saved['meta']['source'],'adjustment':saved['meta']['adjustment'],
             'price_anchor':{'time':event['anchor_time'],'price':event['price'],'index':event['anchor']},
             'center':{'zd':point['zd'],'zg':point['zg']},'prefix_first_confirmation':{'time':event['observed_at'],'index':at},
             'snapshot_audit':record,'false_current_confirmations_after_fix':0,
             'previous_prefix_has_signal':False,'confirmation_prefix_has_signal':True,
             'strict_original_equivalence_proven':False,'execution_allowed':False}
    output=args.source.parent/'audit-result.json';output.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'result':str(output.resolve()),'verified':True,'historical_confirmation':event['observed_at'],
                      'price':event['price'],'false_current_confirmation_removed':True},ensure_ascii=False))


if __name__=='__main__':main()
