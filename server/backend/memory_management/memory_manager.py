from typing import Dict
from .memory_config import MemoryConfig
from .memory_monitor import MemoryMonitor
from .chunk_cache import ChunkCache
from .image_processor import MemoryEfficientProcessor
from .background_cleaner import BackgroundCleaner


class MemoryManager:
    """통합 메모리 관리자"""

    def __init__(self, config: MemoryConfig = None):
        self.config = config or MemoryConfig()

        # 컴포넌트 초기화
        self.monitor = MemoryMonitor()
        self.cache = ChunkCache(self.config.cache_max_size_mb)
        self.processor = MemoryEfficientProcessor(self.config)
        self.background_cleaner = BackgroundCleaner(self.monitor, self.cache, self.config)

        # 백그라운드 작업 시작
        self.background_cleaner.start()

    def get_status_json(self):
        """
        메모리 상태를 JSON 형식으로 반환

        Returns:
            dict: 메모리 및 캐시 상태 정보
        """
        try:
            import psutil
            process = psutil.Process()

            # 메모리 정보
            memory_info = process.memory_info()
            process_mb = memory_info.rss / (1024 * 1024)

            # 시스템 메모리
            system_memory = psutil.virtual_memory()
            system_percent = system_memory.percent

            # 캐시 정보
            cache_info = {
                "cache_size_mb": 0,
                "hit_rate": 0
            }

            # chunk_cache가 있으면 정보 가져오기
            if hasattr(self, 'chunk_cache') and self.chunk_cache:
                cache_info = self.chunk_cache.get_cache_info()

            return {
                "memory": {
                    "process_mb": round(process_mb, 2),
                    "system_percent": round(system_percent, 2)
                },
                "cache": {
                    "cache_size_mb": round(cache_info.get("cache_size_mb", 0), 2),
                    "hit_rate": round(cache_info.get("hit_rate", 0), 2)
                },
                "config": {
                    "cache_max_size_mb": self.config.cache_max_size_mb if hasattr(self, 'config') else 200
                }
            }
        except Exception as e:
            print(f"get_status_json 오류: {e}")
            return {
                "memory": {"process_mb": 0, "system_percent": 0},
                "cache": {"cache_size_mb": 0, "hit_rate": 0},
                "config": {"cache_max_size_mb": 200}
            }

    def get_overall_stats(self) -> Dict:
        """전체 메모리 상태 반환"""
        return {
            "memory": self.monitor.get_memory_usage(),
            "cache": self.cache.get_stats(),
            "processor": self.processor.get_stats(),
            "background_cleaner": self.background_cleaner.get_stats(),
            "config": self.config.__dict__
        }

    def force_cleanup(self) -> Dict:
        """강제 메모리 정리"""
        cleanup_result = self.monitor.force_cleanup()
        self.cache.clear()
        return cleanup_result

    def shutdown(self):
        """메모리 매니저 종료"""
        self.background_cleaner.stop()
        self.cache.clear()
        self.monitor.force_cleanup()
        print("메모리 매니저 종료 완료")