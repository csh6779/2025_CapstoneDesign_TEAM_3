import threading
import time
import gc
from typing import Dict
from .memory_monitor import MemoryMonitor
from .chunk_cache import ChunkCache
from .memory_config import MemoryConfig


class BackgroundCleaner:
    """백그라운드 메모리 정리 작업"""

    def __init__(self, monitor: MemoryMonitor, cache: ChunkCache, config: MemoryConfig):
        self.monitor = monitor
        self.cache = cache
        self.config = config
        self.running = False
        self.thread = None
        self.stats = {
            "cleanup_count": 0,
            "total_freed_mb": 0,
            "last_cleanup": None
        }

    def start(self):
        """백그라운드 정리 작업 시작"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.thread.start()
        print("백그라운드 메모리 정리 작업 시작")

    def stop(self):
        """백그라운드 정리 작업 중지"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("백그라운드 메모리 정리 작업 중지")

    def _cleanup_loop(self):
        """주기적 메모리 정리"""
        while self.running:
            try:
                memory_usage = self.monitor.get_memory_usage()

                if memory_usage["system_percent"] > (self.config.memory_cleanup_threshold * 100):
                    print(f"메모리 사용률 높음: {memory_usage['system_percent']:.1f}%")

                    # 정리 수행
                    cleanup_result = self._perform_cleanup()

                    self.stats["cleanup_count"] += 1
                    self.stats["total_freed_mb"] += cleanup_result["freed_mb"]
                    self.stats["last_cleanup"] = time.time()

                    print(f"메모리 정리 완료: {cleanup_result['freed_mb']:.1f}MB 해제")

                time.sleep(self.config.cache_cleanup_interval)

            except Exception as e:
                print(f"백그라운드 정리 오류: {e}")
                time.sleep(60)

    def _perform_cleanup(self) -> Dict:
        """메모리 정리 수행"""
        before = self.monitor.get_memory_usage()

        # 캐시 정리
        self.cache.clear()

        # 가비지 컬렉션
        gc.collect()

        after = self.monitor.get_memory_usage()

        return {
            "before_mb": before["process_mb"],
            "after_mb": after["process_mb"],
            "freed_mb": before["process_mb"] - after["process_mb"]
        }

    def get_stats(self) -> Dict:
        """정리 통계 반환"""
        return {
            **self.stats,
            "is_running": self.running,
            "config_interval": self.config.cache_cleanup_interval,
            "config_threshold": self.config.memory_cleanup_threshold
        }
