import threading,time,unittest
from concurrent.futures import ThreadPoolExecutor
from fastapi import HTTPException
from web.compute_budget import budget,ByteCache,status
from web import realtime_panel as live
from tests.test_stroke_signals import market_bars
from datetime import datetime,timedelta


class ComputeBudgetTests(unittest.TestCase):
    def test_only_one_request_allocates_and_nested_same_thread_does_not_deadlock(self):
        with budget('outer'):
            with budget('nested'):self.assertEqual(status()['active'],'outer')
            with ThreadPoolExecutor(max_workers=1) as pool:
                def competing():
                    try:
                        with budget('competitor'):raise AssertionError('Overlapped heavy computations')
                    except HTTPException as e:return e.status_code,e.headers
                code,headers=pool.submit(competing).result(timeout=3)
            self.assertEqual(code,429);self.assertEqual(headers['Retry-After'],'10')
        with budget('after'):self.assertEqual(status()['active'],'after')

    def test_byte_cache_capacity_and_immutability(self):
        cache=ByteCache(max_bytes=8,max_entries=2)
        cache.put('a',b'1234');cache.put('b',b'5678');cache.get('a')
        cache.put('c',b'9012');self.assertIsNone(cache.get('b'));self.assertEqual(cache.bytes,8)
        cache.put('oversized',b'123456789');self.assertIsNone(cache.get('oversized'))
        self.assertLessEqual(cache.bytes,8)
        with self.assertRaises(TypeError):cache.put('graph',{'unbounded':'mutable object'})

    def test_cached_model_is_compressed_and_mutation_cannot_contaminate_next_request(self):
        import gzip,pickle
        data=market_bars(40);now=datetime.fromisoformat(data[-1].closed_at)+timedelta(minutes=1)
        live.structure_cache.clear()
        first=live.make_panel('sh600261','day',data,now,reuse_structure=True)
        self.assertTrue(live.structure_cache.items)
        self.assertTrue(all(isinstance(v,bytes) for v in live.structure_cache.items.values()))
        first['stroke_model']['signals'].append({'id':'must-not-leak'})
        second=live.make_panel('sh600261','day',data,now,reuse_structure=True)
        self.assertFalse(any(p['id']=='must-not-leak' for p in second['stroke_model']['signals']))
        self.assertLessEqual(live.structure_cache.bytes,8*1024*1024)


if __name__=='__main__':unittest.main()
