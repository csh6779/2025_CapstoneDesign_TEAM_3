from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class MemoryConfig:
    """메모리 관리 설정"""
    max_image_size_mb: int = 500
    chunk_size: int = 512
    max_concurrent_processing: int = 2
    memory_cleanup_threshold: float = 0.8
    cache_cleanup_interval: int = 300
    cache_max_size_mb: int = 200

@dataclass
class ProcessingResult:
    """처리 결과 데이터"""
    chunk_x: int
    chunk_y: int
    progress: float
    memory_usage: Dict
    cache_size_mb: float
    success: bool = True
    error_message: Optional[str] = None