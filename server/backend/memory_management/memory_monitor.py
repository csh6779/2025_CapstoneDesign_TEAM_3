import psutil
import gc
from typing import Dict


class MemoryMonitor:
    """시스템 메모리 모니터링"""

    def __init__(self):
        self.process = psutil.Process()
        self.start_memory = self.get_memory_usage()

    def get_memory_usage(self) -> Dict:
        """현재 메모리 사용량 조회"""
        memory_info = self.process.memory_info()
        system_memory = psutil.virtual_memory()

        return {
            "process_mb": memory_info.rss / (1024 * 1024),
            "process_percent": self.process.memory_percent(),
            "system_available_mb": system_memory.available / (1024 * 1024),
            "system_percent": system_memory.percent,
            "is_critical": system_memory.percent > 85
        }

    def should_cleanup(self, threshold: float = 0.8) -> bool:
        """메모리 정리가 필요한지 확인"""
        return self.get_memory_usage()["system_percent"] / 100 > threshold

    def force_cleanup(self) -> Dict:
        """강제 메모리 정리"""
        before = self.get_memory_usage()
        gc.collect()
        after = self.get_memory_usage()

        return {
            "before_mb": before["process_mb"],
            "after_mb": after["process_mb"],
            "freed_mb": before["process_mb"] - after["process_mb"]
        }

    def get_cleanup_stats(self) -> Dict:
        """정리 통계 반환"""
        return {
            "memory_saved_mb": max(0, self.start_memory["process_mb"] - self.get_memory_usage()["process_mb"]),
            "current_usage": self.get_memory_usage()
        }