"""Exercise all six branches on declared structures, including absent retests.

Synthetic fixtures verify rule symmetry; they are never shown as market data.
"""
import unittest
from chanmodel.model import Candle
from chanmodel.v2.divergence import compare_divergences,make_signals,anchor_signals_to_extremes


def scenario(mirrored=False):
    values=[30,20,26,21,25,12,18,13,17,8,11,10,15]
    if mirrored:values=[50-value for value in values]
    bars=[Candle(i,p,p,p,p,f'2026-01-01T{i:02}:00:00+08:00') for i,p in enumerate(values)]
    units=[dict(id=f'u{i}',rank=0,kind='base_segment',direction='up' if b>a else 'down',
                start=i,end=i+1,start_price=a,end_price=b,low=min(a,b),high=max(a,b),
                state='complete',completed_at=i+1,completion={'rule':'base_segment_confirmed'})
           for i,(a,b) in enumerate(zip(values,values[1:]))]
    centers=[]
    for name,indices in [('A',[1,2,3]),('B',[5,6,7])]:
        seed=[units[index] for index in indices]
        centers.append(dict(id=name,rank=1,zd=max(unit['low'] for unit in seed),zg=min(unit['high'] for unit in seed),
                            dd=min(unit['low'] for unit in seed),gg=max(unit['high'] for unit in seed),
                            start=seed[0]['start'],end=seed[-1]['end'],seed_end=seed[-1]['end'],
                            seed_indices=indices,attempts=[],departure=None,available_at=seed[-1]['end'],certificate={'passed':True}))
    centers[-1].update(attempts=[dict(leave_index=8,return_index=9,relation='outside',available_at=10)],
                        departure=dict(return_index=9,side='buy' if mirrored else 'sell',available_at=10,
                                       boundary=centers[-1]['zg' if mirrored else 'zd'],leave_id='u8',return_id='u9'))
    sign=1 if mirrored else -1
    histogram=[dict(dif=2.,dea=2.,histogram=float(sign)) for _ in values]
    for i in [4,5]:histogram[i]['histogram']=4.*sign
    for i in [6,7]:histogram[i].update(dif=0.,dea=0.)
    return units,centers,bars,histogram


class SixSignalTests(unittest.TestCase):
    def test_internal_price_extreme_preserves_identity_and_later_availability(self):
        bars=[Candle(0,10,11,9,10),Candle(1,10,12,7,9),Candle(2,9,10,8,9),Candle(3,9,11,8,10)]
        points=[dict(id='stable-first-buy',**{'class':'first_buy'},side='buy',anchor=2,
                     price=9,terminal_range=[0,2],available_at=3,invalidation=8)]
        anchor_signals_to_extremes(points,bars)
        point=points[0]
        self.assertEqual((point['id'],point['anchor'],point['price'],point['decomposition_end'],point['available_at']),
                         ('stable-first-buy',1,7,2,3))
        self.assertEqual(point['state'],'awaiting_lower_confirmation')
        later=bars+[Candle(4,8,9,6,7)]
        anchor_signals_to_extremes(points,later)
        self.assertEqual(point['state'],'invalidated')
        self.assertEqual(point['decomposition_end'],2)

    def test_mirrored_structures_produce_all_six_classes_without_confirming_candidates(self):
        classes=set()
        for mirrored in [False,True]:
            units,centers,bars,histogram=scenario(mirrored)
            comparisons=compare_divergences(units,centers,bars,histogram,1,len(bars)-1)
            self.assertEqual(comparisons[0]['blocked_gates'],[])
            points=make_signals(units,centers,comparisons,bars,1,histogram)
            classes.update(point['class'] for point in points)
            self.assertTrue(all(point['state']!='confirmed' for point in points))
            first=next(point for point in points if point['class'].startswith('first_'))
            second=next(point for point in points if point['class'].startswith('second_'))
            self.assertEqual(second['first_signal'],first['id'])
            self.assertGreater(second['available_at'],first['available_at'])
        self.assertEqual(classes,{'first_buy','second_buy','third_buy','first_sell','second_sell','third_sell'})

    def test_unfinished_first_retest_cannot_produce_second_class(self):
        for mirrored in [False,True]:
            units,centers,bars,histogram=scenario(mirrored)
            units=units[:10];bars=bars[:11];histogram=histogram[:11]
            comparisons=compare_divergences(units,centers,bars,histogram,1,len(bars)-1)
            points=make_signals(units,centers,comparisons,bars,1,histogram)
            self.assertTrue(any(point['class'].startswith('first_') for point in points))
            self.assertFalse(any(point['class'].startswith('second_') for point in points))

    def test_missing_trend_gate_cannot_be_relabelled_first_or_second(self):
        units,centers,bars,histogram=scenario()
        comparisons=compare_divergences(units,[centers[-1]],bars,histogram,1,len(bars)-1)
        self.assertFalse(comparisons[0]['gates']['two_separated_same_rank_centers'])
        points=make_signals(units,[centers[-1]],comparisons,bars,1,histogram)
        self.assertFalse(any(point['class'].startswith(('first_','second_')) for point in points))


if __name__=='__main__':unittest.main()
