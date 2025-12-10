import numpy as np
import threading
import time
from typing import Optional, Dict


class ChunkCache:
    """메모리 효율적 청크 캐시"""

    def __init__(self, max_size_mb: int = 200):
        self.max_size_mb = max_size_mb
        self.cache = {}
        self.current_size_mb = 0
        self._lock = threading.Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    def put(self, chunk_id: str, data: np.ndarray) -> bool:
        """청크 데이터 캐시에 저장"""
        size_mb = data.nbytes / (1024 * 1024)

        with self._lock:
            # 캐시 크기 초과 시 LRU 제거
            while self.current_size_mb + size_mb > self.max_size_mb and self.cache:
                self._evict_lru()

            if self.current_size_mb + size_mb <= self.max_size_mb:
                self.cache[chunk_id] = {
                    'data': data.copy(),
                    'size_mb': size_mb,
                    'last_access': time.time()
                }
                self.current_size_mb += size_mb
                return True
            return False

    def get(self, chunk_id: str) -> Optional[np.ndarray]:
        """캐시에서 청크 데이터 조회"""
        with self._lock:
            if chunk_id in self.cache:
                self.cache[chunk_id]['last_access'] = time.time()
                self.stats["hits"] += 1
                return self.cache[chunk_id]['data']

            self.stats["misses"] += 1
            return None

    def _evict_lru(self):
        """가장 오래된 캐시 항목 제거"""
        if not self.cache:
            return

        oldest_id = min(self.cache.keys(),
                        key=lambda k: self.cache[k]['last_access'])

        removed = self.cache.pop(oldest_id)
        self.current_size_mb -= removed['size_mb']
        self.stats["evictions"] += 1

    def clear(self):
        """전체 캐시 초기화"""
        with self._lock:
            self.cache.clear()
            self.current_size_mb = 0

    def get_stats(self) -> Dict:
        """캐시 통계 반환"""
        with self._lock:
            hit_rate = self.stats["hits"] / max(1, self.stats["hits"] + self.stats["misses"])
            return {
                **self.stats,
                "hit_rate": hit_rate,
                "cache_size_mb": self.current_size_mb,
                "cache_items": len(self.cache),
                "utilization": self.current_size_mb / self.max_size_mb
            }