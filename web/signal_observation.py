"""Separate a snapshot audit from a newly witnessed closed-bar transition.

Starting this service today does not make an old structural signal new today.
Historical first confirmation is available only from prefix replay.
"""
from collections import OrderedDict
import threading

sessions=OrderedDict()
guard=threading.RLock()


def observe(code,period,resolution,points,bars,now):
    times=[bar.closed_at for bar in bars];indices={stamp:i for i,stamp in enumerate(times)}
    key=(code,period,resolution)
    with guard:
        previous=sessions.get(key)
        watermark=previous['last_closed'] if previous else None
        advanced=bool(watermark and times[-1]>watermark)
        prior=previous['points'] if previous else {}
        current={};records=[];confirmations=[]
        for point in points:
            anchor=point['event_time']
            available=point.get('available_at',point.get('anchor',0))
            evidence=times[available] if isinstance(available,int) and 0<=available<len(times) else None
            identity=(point['class'],point['side'],point.get('rank',0),anchor,point['price'],point.get('zd'),point.get('zg'))
            geometry=(point.get('invalidation'),tuple(times[i] for i in point.get('terminal_range',[]) if 0<=i<len(times)),evidence)
            old=prior.get(identity)
            passed=bool(point.get('rule_audit',{}).get('passed') and point.get('state')!='invalidated' and evidence)
            same=bool(old and old['geometry']==geometry)
            witnessed=old.get('witness') if same else None
            new_candidate=bool(advanced and evidence and evidence>watermark and not old and point.get('state')!='invalidated')
            candidate_origin='live_closed_bar_candidate' if new_candidate else old.get('candidate_origin','snapshot_audit') if same else 'snapshot_audit'
            # New data must itself contain the evidence. Repeated checks,
            # service restarts and revisions to older bars establish audits.
            if not witnessed and passed and advanced and evidence>watermark and (not old or not old['passed']):
                witnessed={'checked_at':now.isoformat(),'evidence_time':evidence}
            state='invalidated' if point.get('state')=='invalidated' else 'confirmed' if passed and witnessed else 'snapshot_validated' if passed else point.get('state','candidate')
            if old and old.get('witness') and (not same or not passed) and state!='invalidated':state='withdrawn'
            record={'id':point['id'],'state':state,'current_state':state,
                    'first_checked_at':old['first_checked_at'] if old else now.isoformat(),'audited_at':now.isoformat(),
                    'snapshot_passed':passed,'evidence_at':evidence,'evidence_index':available,
                    'confirmation_origin':'live_closed_bar_transition' if witnessed and state=='confirmed' else candidate_origin,
                    'historical_first_confirmation_verified':False}
            if witnessed and passed and state=='confirmed' and witnessed['evidence_time'] in indices:
                record['confirmed_at']=witnessed['checked_at']
                confirmations.append({'signal_id':point['id'],'class':point['class'],'side':point['side'],'rank':point.get('rank',0),
                    'resolution':resolution,'anchor':point['anchor'],'anchor_time':anchor,'price':point['price'],
                    'observed_index':indices[witnessed['evidence_time']],'evidence_at':witnessed['evidence_time'],
                    'observed_at':witnessed['checked_at'],'confirmed_at':witnessed['checked_at'],'event':'confirmed',
                    'point':point,'execution_allowed':False,'rule_audit':point.get('rule_audit'),
                    'confirmation_origin':'live_closed_bar_transition','historical_first_confirmation_verified':False,
                    'confirmation_semantics':('stroke_rule_' if resolution=='stroke' else '')+'live_closed_bar_transition; first_observed_online_not_historical_replay'})
            records.append(record)
            current[identity]={'geometry':geometry,'passed':passed,'witness':witnessed,
                               'candidate_origin':candidate_origin,
                               'first_checked_at':record['first_checked_at']}
        sessions[key]={'last_closed':times[-1],'points':current};sessions.move_to_end(key)
        while len(sessions)>16:sessions.popitem(last=False)
        return records,confirmations
