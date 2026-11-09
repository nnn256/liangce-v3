"""Fine stroke rules remain causal and distinct from original recursive gates."""
from datetime import datetime,timedelta,timezone
import math,unittest
from chanmodel.model import Candle
from chanmodel.stroke_signals import PriceRanges,replay,snapshot,analyze_strokes
from chanmodel.causal_portfolio import simulate,CostModel


def market_bars(n=300):
    result=[];day=datetime(2025,1,2,15,tzinfo=timezone(timedelta(hours=8)))
    for i in range(n):
        close=30+math.sin(i/4)*3+math.sin(i/18)*5+i*.005
        result.append(Candle(i,close-.1,close+.4,close-.5,close,(day+timedelta(days=i)).isoformat(),100000,True))
    return result


class FineStrokeTests(unittest.TestCase):
    def test_stroke_center_ranges_include_original_candle_wicks(self):
        bars=[Candle(i,10,11,9,10,f'2025-01-{i+1:02}T15:00:00+08:00',100) for i in range(7)]
        bars[3]=Candle(3,10,17,8,10,bars[3].closed_at,100)
        strokes=[{'id':f'p{i}','start':i*2,'end':i*2+2,'start_price':9 if i%2==0 else 11,'end_price':11 if i%2==0 else 9,
                  'low':9,'high':11,'direction':'up' if i%2==0 else 'down','basis_at':min(6,i*2+2),'state':'confirmed'} for i in range(3)]
        result=analyze_strokes(strokes,bars,[{'histogram':0} for _ in bars])
        self.assertEqual(result['centers'][0]['gg'],17)
        self.assertEqual(result['centers'][0]['dd'],8)
    def test_sparse_extrema_matches_direct_ranges_and_first_equal_extreme(self):
        bars=market_bars(40);ranges=PriceRanges(bars)
        for start in range(40):
            for end in range(start,40):
                low=min(bars[start:end+1],key=lambda b:b.low);high=max(bars[start:end+1],key=lambda b:b.high)
                self.assertEqual(ranges.query(start,end),(low.low,low.pos,high.high,high.pos))

    def test_append_future_bars_does_not_rewrite_past_observed_events(self):
        bars=market_bars();early=replay(bars[:190],'day');full=replay(bars,'day')
        self.assertGreater(len(early['signal_events']),0)
        later=[item for item in full['signal_events'] if item['observed_index']<190]
        self.assertEqual(early['signal_events'],later)
        for event in full['confirmations']:
            self.assertLessEqual(event['anchor'],event['observed_index'])
            self.assertEqual(event['definition_mode'],'stroke_proxy')
            self.assertFalse(event['execution_allowed'])
            point=event['point'];prefix=bars[:event['observed_index']+1]
            candidates=snapshot(prefix)['signals']
            self.assertTrue(any(item['id']==point['id'] for item in candidates))

    def test_volume_of_opening_bar_cannot_change_prior_observed_order_eligibility(self):
        bars=[Candle(i,10,11,9.8,10,datetime(2025,1,i+1,15,tzinfo=timezone(timedelta(hours=8))).isoformat(),100000,True) for i in range(5)]
        event={'signal_id':'buy','event':'confirmed','side':'buy','class':'first_buy','rank':0,'observed_index':0,'invalidation':9}
        closes={b.closed_at[:10]:b.close for b in bars}
        first=simulate(bars,bars,[event],closes,period='day')
        changed=list(bars);b=bars[1];changed[1]=Candle(b.pos,b.open,b.high,b.low,b.close,b.closed_at,0,True)
        second=simulate(changed,changed,[event],closes,period='day')
        one=next(order for order in first['orders'] if order['state']=='filled')
        two=next(order for order in second['orders'] if order['state']=='filled')
        self.assertEqual((one['bar_index'],one['price'],one['shares']),(two['bar_index'],two['price'],two['shares']))
        self.assertGreater(one['time'],bars[0].closed_at)


if __name__=='__main__':unittest.main()
