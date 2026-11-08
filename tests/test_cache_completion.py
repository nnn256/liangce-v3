"""Slow upstream work must not consume a cache entry's entire TTL."""
from pathlib import Path
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'web'));sys.path.insert(0,str(ROOT/'scripts'))
import main

class CacheCompletionTests(unittest.TestCase):
    def test_intraday_ttl_starts_when_result_is_ready(self):
        main._intraday_radar_cache.clear()
        payload={'status':'ok','updatedAt':123,'anomalies':[]}
        with patch.object(main.time,'time',side_effect=[100.,110.,111.]),patch.object(main.qds,'get_real_intraday_radar',return_value=payload) as upstream:
            first=main.api_quant_intraday_radar('000530.SZ',20)
            second=main.api_quant_intraday_radar('000530.SZ',20)
        self.assertEqual(first.body,second.body)
        self.assertEqual(upstream.call_count,1)
        self.assertEqual(main._intraday_radar_cache[('000530.SZ',20)][0],110.)
        main._intraday_radar_cache.clear()

if __name__=='__main__':unittest.main()
