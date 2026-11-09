"""Six explicitly named stroke rules with prefix-observed availability.

Stroke overlaps are an observation scale, not completed lower movement types.
Rule confirmation means the stroke rule is closed and survived observation;
it is never presented as a proof of the full original multilevel definition.
"""
import math
from .model import Config
from .structure import merge_bars,fractals_at,strokes_at
from .signals import macd
from .causal_replay import StreamingStructure

PROFILE='stroke_actual_extreme_center_first_retest_v2'
CLASSES=('first_buy','second_buy','third_buy','first_sell','second_sell','third_sell')
FINE=Config(stroke_mode='loose',macd_multiplier=2)


class PriceRanges:
    """Append-only sparse extrema; exact range checks without rescanning prices."""
    def __init__(self,bars=()):
        self.levels=[];self.size=0
        for bar in bars:self.append(bar)

    @staticmethod
    def join(a,b):
        low=min(a[:2],b[:2]);high=max((a[2],-a[3]),(b[2],-b[3]))
        return low[0],low[1],high[0],-high[1]

    def append(self,bar):
        if not self.levels:self.levels.append([])
        self.levels[0].append((bar.low,bar.pos,bar.high,bar.pos));self.size+=1
        level=1
        while 1<<level<=self.size:
            if len(self.levels)<=level:self.levels.append([])
            start=self.size-(1<<level);half=1<<(level-1)
            self.levels[level].append(self.join(self.levels[level-1][start],self.levels[level-1][start+half]));level+=1

    def query(self,start,end):
        if not 0<=start<=end<self.size:raise ValueError('range outside visible prefix')
        level=(end-start+1).bit_length()-1
        return self.join(self.levels[level][start],self.levels[level][end-(1<<level)+1])


def stroke_centers(strokes):
    centers=[];cursor=0
    while cursor+2<len(strokes):
        seed=strokes[cursor:cursor+3];zd=max(s['low'] for s in seed);zg=min(s['high'] for s in seed)
        if zd>=zg:cursor+=1;continue
        members=list(range(cursor,cursor+3));attempts=[];leave=None;departure=None;j=cursor+3
        while j<len(strokes):
            current=strokes[j]
            if leave is None:
                extends=current['high']>zg if current['direction']=='up' else current['low']<zd
                if extends:leave=j
                else:members.append(j)
                j+=1;continue
            outgoing=strokes[leave];up=outgoing['direction']=='up';edge=current['low'] if up else current['high']
            relation='outside' if (edge>zg if up else edge<zd) else 'crossed' if (edge<zd if up else edge>zg) else 'inside'
            attempt={'leave_index':leave,'return_index':j,'side':'buy' if up else 'sell','relation':relation,
                     'available_at':max(strokes[k]['basis_at'] for k in members+[leave,j])}
            attempts.append(attempt)
            if relation=='outside':departure=attempt;break
            if relation=='crossed':members.append(leave);leave=j
            else:members.extend([leave,j]);leave=None
            j+=1
        centers.append({'id':f"pc:{seed[0]['start']}:{seed[-1]['end']}",'rank':0,'resolution':'stroke',
                        'start':seed[0]['start'],'end':strokes[members[-1]]['end'],'zd':zd,'zg':zg,
                        'dd':min(strokes[k]['low'] for k in members),'gg':max(strokes[k]['high'] for k in members),
                        'seed_indices':list(range(cursor,cursor+3)),'formed_at':max(s['basis_at'] for s in seed),
                        'attempts':attempts,'departure':departure,'state':'broken' if departure else 'formed',
                        'definition_mode':'stroke_overlap_proxy','sublevel_movement_types_verified':False})
        if not departure:break
        cursor=departure['return_index']
    return centers


def analyze_strokes(strokes,bars,histogram,*,check_invalidation=True,ranges=None):
    ranges=ranges or PriceRanges(bars)
    closed=[dict(s) for s in strokes if s['state']=='confirmed']
    for unit in closed:
        low,_,high,_=ranges.query(unit['start'],unit['end'])
        unit.update(low=low,high=high)
    centers=stroke_centers(closed);points=[]
    positive=[0.];negative=[0.]
    for value in histogram:
        h=value['histogram'];positive.append(positive[-1]+max(0.,h));negative.append(negative[-1]+max(0.,-h))
    def force(s):
        values=positive if s['direction']=='up' else negative
        return values[s['end']+1]-values[s['start']]
    def emit(kind,unit,center,at,limit,**proof):
        side='buy' if kind.endswith('buy') else 'sell';low,low_at,high,high_at=ranges.query(unit['start'],unit['end'])
        pivot=bars[low_at if side=='buy' else high_at];price=low if side=='buy' else high
        if not kind.startswith('third_'):limit=price
        later=ranges.query(pivot.pos+1,len(bars)-1) if pivot.pos+1<len(bars) else None
        ended=bool(check_invalidation and later and (later[0]<=limit if side=='buy' else later[2]>=limit))
        gates={'three_stroke_overlap':center['zd']<center['zg'],'terminal_stroke_completed':unit['state']=='confirmed',
               'terminal_extreme_recorded':True,'evidence_not_future':at<len(bars),'not_invalidated_at_observation':not ended,**proof.pop('gates',{})}
        point={'id':f"ps:{kind}:{center['id']}:{unit['end']}",'class':kind,'side':side,'rank':0,'resolution':'stroke',
               'anchor':pivot.pos,'price':price,'terminal_range':[unit['start'],unit['end']],'decomposition_end':unit['end'],
               'center_id':center['id'],'zd':center['zd'],'zg':center['zg'],'available_at':at,
               'available_time':bars[at].closed_at,'event_time':pivot.closed_at,'invalidation':limit,
               'state':'invalidated' if ended else 'candidate','profile':PROFILE,'definition_mode':'stroke_proxy',
               'rule_audit':{'gates':gates,'passed':all(gates.values()),'missing':[k for k,v in gates.items() if not v]},
               'strict_original_equivalence_proven':False,'execution_allowed':False,**proof}
        points.append(point);return point
    for ci,center in enumerate(centers):
        for attempt in center['attempts']:
            if attempt['relation']=='outside':
                unit=closed[attempt['return_index']];side=attempt['side']
                emit('third_'+side,unit,center,attempt['available_at'],center['zg' if side=='buy' else 'zd'],
                     leave_id=closed[attempt['leave_index']]['id'],return_id=unit['id'],
                     gates={'completed_departure_and_first_return':True,'first_return_strictly_outside':True})
                break
        entering=center['seed_indices'][0]-1
        if entering<0:continue
        a=closed[entering];prior=centers[ci-1] if ci else None
        for attempt in center['attempts']:
            idx=attempt['leave_index'];c=closed[idx]
            if c['direction']!=a['direction']:continue
            side='buy' if c['direction']=='down' else 'sell'
            separated=bool(prior and (center['gg']<prior['dd'] if side=='buy' else center['dd']>prior['gg']))
            extreme=c['low']<a['low'] if side=='buy' else c['high']>a['high']
            af,cf=force(a),force(c);weak=af>1e-12 and cf<af
            if not (separated and extreme and weak):continue
            first=emit('first_'+side,c,center,max(center['formed_at'],c['basis_at']),c['low' if side=='buy' else 'high'],
                       comparison={'a':a['id'],'c':c['id'],'a_area':af,'c_area':cf,'same_direction':True,'prior_center':prior['id']},
                       gates={'two_separated_stroke_centers':True,'new_extreme':True,'weaker_same_direction_force':True})
            if idx+2>=len(closed):continue
            rebound,ret=closed[idx+1:idx+3]
            holds=ret['low']>c['low'] if side=='buy' else ret['high']<c['high']
            path=ranges.query(first['anchor']+1,ret['end']) if first['anchor']<ret['end'] else None
            first_survives=path is not None and (path[0]>first['invalidation'] if side=='buy' else path[2]<first['invalidation'])
            if ret['direction']!=c['direction'] or rebound['direction']==c['direction'] or not holds or not first_survives:continue
            emit('second_'+side,ret,center,max(first['available_at'],rebound['basis_at'],ret['basis_at']),ret['low' if side=='buy' else 'high'],
                 first_signal=first['id'],first_anchor=first['anchor'],
                 gates={'prior_first_context_present':True,'first_post_turn_retest':True,'first_extreme_held':True,'entire_rebound_retest_path_holds_first':True})
    # One center may revisit the same leave in multiple attempts.
    unique={point['id']:point for point in points}
    return {'centers':centers,'signals':sorted(unique.values(),key=lambda p:(p['anchor'],p['id'])),'strokes':strokes,'profile':PROFILE}


def snapshot(bars,config=FINE):
    merged=merge_bars(bars,config);fractals=fractals_at(merged);strokes,_=strokes_at(fractals,config)
    return {**analyze_strokes(strokes,bars,macd(bars,config)),'fractals':fractals}


def replay(bars,period,config=FINE,progress=None):
    stream=StreamingStructure(config,segments=False);records={};events=[];confirmations=[];last_signature=None;current=None
    ranges=PriceRanges()
    def event(rec,kind,bar,**extra):
        p=rec['point'];item={'sequence':len(events),'event':kind,'signal_id':p['id'],'class':p['class'],'side':p['side'],
                             'rank':0,'resolution':'stroke','anchor':p['anchor'],'anchor_time':p['event_time'],'price':p['price'],
                             'invalidation':p['invalidation'],'observed_index':bar.pos,'observed_at':bar.closed_at,
                             'confirmed_at':rec.get('confirmed_at'),'definition_mode':'stroke_proxy','execution_allowed':False,**extra}
        events.append(item);return item
    for i,bar in enumerate(bars):
        if not bar.closed:raise ValueError('Replay accepts closed bars only')
        ranges.append(bar)
        for rec in records.values():
            if rec['state'] not in {'candidate','confirmed'}:continue
            p=rec['point']
            if bar.pos>p['anchor'] and (bar.low<=p['invalidation'] if p['side']=='buy' else bar.high>=p['invalidation']):
                rec.update(state='invalidated',invalidated_at=bar.closed_at);event(rec,'invalidated',bar)
        changed=stream.append(bar)
        if changed:
            closed=[s for s in stream.strokes if s['state']=='confirmed']
            signature=tuple((s['id'],s['basis_at']) for s in closed)
            if signature!=last_signature:
                last_signature=signature;current=analyze_strokes(stream.strokes,stream.bars,stream.histogram,ranges=ranges)
                present=set()
                for point in current['signals']:
                    ident=point['id'];present.add(ident)
                    if ident not in records:
                        rec={'id':ident,'point':point,'state':'candidate','first_seen_at':bar.closed_at,'confirmed_at':None}
                        records[ident]=rec;event(rec,'candidate_observed',bar)
                    rec=records[ident];old=rec['point']
                    revised=any(old.get(k)!=point.get(k) for k in ['anchor','price','invalidation'])
                    # Reports are newly built immutable objects; later prefixes
                    # replace this reference and never mutate past evidence.
                    rec['point']=point
                    if point['state']=='invalidated':
                        if rec['state']!='invalidated':rec.update(state='invalidated',invalidated_at=bar.closed_at);event(rec,'invalidated',bar)
                    elif revised and rec['state']=='confirmed':rec.update(state='withdrawn',withdrawn_at=bar.closed_at);event(rec,'withdrawn',bar)
                    elif rec['state']=='candidate' and point['rule_audit']['passed']:
                        rec.update(state='confirmed',confirmed_at=bar.closed_at,confirmed_index=i)
                        confirmations.append(event(rec,'confirmed',bar,point=point,rule_audit=point['rule_audit'],
                                                   confirmation_semantics='stroke_rule_prefix_observed; original_multilevel_confirmation_not_proven'))
                for ident,rec in records.items():
                    if ident not in present and rec['state'] in {'candidate','confirmed'}:
                        rec.update(state='withdrawn',withdrawn_at=bar.closed_at);event(rec,'withdrawn',bar)
        if progress and (i%500==0 or i==len(bars)-1):progress(i+1,len(bars))
    return {'profile':PROFILE,'definition_mode':'stroke_proxy','signals':[rec['point'] for rec in records.values()],
            'confirmations':confirmations,'signal_events':events,
            'confirmation_records':[{k:v for k,v in rec.items() if k!='point'} for rec in records.values()],
            'strokes':stream.strokes,'centers':current['centers'] if current else [],'fractals':stream.fractals}
