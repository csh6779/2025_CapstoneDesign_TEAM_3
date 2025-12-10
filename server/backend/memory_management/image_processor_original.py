import asyncio
import os
from pathlib import Path
from typing import AsyncGenerator, Tuple, Dict
from PIL import Image
import numpy as np
from cloudvolume import CloudVolume

from .memory_config import MemoryConfig, ProcessingResult
from .memory_monitor import MemoryMonitor
from .chunk_cache import ChunkCache


class MemoryEfficientProcessor:
    """메모리 효율적 이미지 처리"""

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.monitor = MemoryMonitor()
        self.cache = ChunkCache(config.cache_max_size_mb)

    async def validate_image_size(self, file_path: str) -> Tuple[bool, Dict]:
        """이미지 크기 검증"""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                mode = img.mode

                # 예상 메모리 사용량 계산
                channels = 3 if mode in ['RGB', 'RGBA'] else 1
                estimated_mb = (width * height * channels) / (1024 * 1024)

                is_valid = estimated_mb <= self.config.max_image_size_mb

                return is_valid, {
                    "width": width,
                    "height": height,
                    "mode": mode,
                    "channels": channels,
                    "estimated_mb": estimated_mb,
                    "max_allowed_mb": self.config.max_image_size_mb
                }
        except Exception as e:
            return False, {"error": str(e)}

    async def process_image_streaming(self,
                                      image_path: str,
                                      volume_path: str) -> AsyncGenerator[ProcessingResult, None]:
        """메모리 효율적 스트리밍 이미지 처리"""

        try:
            # 이미지 메타데이터 로드
            is_valid, meta = await self.validate_image_size(image_path)
            if not is_valid:
                yield ProcessingResult(
                    chunk_x=0, chunk_y=0, progress=0,
                    memory_usage=self.monitor.get_memory_usage(),
                    cache_size_mb=self.cache.current_size_mb,
                    success=False,
                    error_message=f"Invalid image: {meta.get('error', 'Size too large')}"
                )
                return

            width, height, channels = meta["width"], meta["height"], meta["channels"]

            # CloudVolume 설정
            volume_info = self._create_volume_info(width, height, channels)
            vol = CloudVolume(f"precomputed://file://{volume_path}",
                              info=volume_info, compress=False, progress=False)
            vol.commit_info()

            # 청크 처리
            async for result in self._process_chunks(image_path, vol, width, height, meta["mode"]):
                yield result

        except Exception as e:
            yield ProcessingResult(
                chunk_x=0, chunk_y=0, progress=0,
                memory_usage=self.monitor.get_memory_usage(),
                cache_size_mb=self.cache.current_size_mb,
                success=False,
                error_message=str(e)
            )

    async def _process_chunks(self, image_path: str, vol: CloudVolume,
                              width: int, height: int, mode: str) -> AsyncGenerator[ProcessingResult, None]:
        """청크 단위 처리"""

        total_chunks = ((width // self.config.chunk_size) + 1) * ((height // self.config.chunk_size) + 1)
        processed_chunks = 0

        for y in range(0, height, self.config.chunk_size):
            for x in range(0, width, self.config.chunk_size):
                # 메모리 압박 시 대기
                while self.monitor.should_cleanup(self.config.memory_cleanup_threshold):
                    await asyncio.sleep(0.1)
                    self.monitor.force_cleanup()
                    self.cache.clear()

                try:
                    # 청크 처리
                    success = await self._process_single_chunk(image_path, vol, x, y, width, height, mode)
                    processed_chunks += 1
                    progress = (processed_chunks / total_chunks) * 100

                    yield ProcessingResult(
                        chunk_x=x,
                        chunk_y=y,
                        progress=progress,
                        memory_usage=self.monitor.get_memory_usage(),
                        cache_size_mb=self.cache.current_size_mb,
                        success=success
                    )

                except Exception as e:
                    yield ProcessingResult(
                        chunk_x=x,
                        chunk_y=y,
                        progress=(processed_chunks / total_chunks) * 100,
                        memory_usage=self.monitor.get_memory_usage(),
                        cache_size_mb=self.cache.current_size_mb,
                        success=False,
                        error_message=str(e)
                    )

                # 주기적 메모리 정리
                if processed_chunks % 10 == 0:
                    self.monitor.force_cleanup()

    async def _process_single_chunk(self, image_path: str, vol: CloudVolume,
                                    x: int, y: int, width: int, height: int, mode: str) -> bool:
        """단일 청크 처리"""
        chunk_id = f"{x}_{y}"

        # 캐시 확인
        cached_data = self.cache.get(chunk_id)
        if cached_data is not None:
            return self._write_chunk_to_volume(vol, cached_data, x, y)

        # 청크 영역 계산
        chunk_width = min(self.config.chunk_size, width - x)
        chunk_height = min(self.config.chunk_size, height - y)

        # 청크 로드
        with Image.open(image_path) as img:
            chunk_img = img.crop((x, y, x + chunk_width, y + chunk_height))
            if mode == 'RGBA':
                chunk_img = chunk_img.convert('RGB')
            chunk_array = np.array(chunk_img)

        # 캐시 저장
        self.cache.put(chunk_id, chunk_array)

        # 볼륨 기록
        return self._write_chunk_to_volume(vol, chunk_array, x, y)

    def _write_chunk_to_volume(self, vol: CloudVolume, chunk_data: np.ndarray, x: int, y: int) -> bool:
        """청크 데이터를 CloudVolume에 기록"""
        try:
            if len(chunk_data.shape) == 2:
                chunk_data = np.expand_dims(chunk_data, axis=-1)

            data = np.expand_dims(chunk_data, axis=2)
            data = np.transpose(data, (1, 0, 2, 3))

            h, w = chunk_data.shape[:2]
            vol[x:x + w, y:y + h, 0:1] = data
            return True

        except Exception as e:
            print(f"청크 기록 실패 ({x},{y}): {e}")
            return False

    def _create_volume_info(self, width: int, height: int, channels: int):
        """CloudVolume 정보 생성"""
        return CloudVolume.create_new_info(
            num_channels=channels,
            layer_type="image",
            data_type="uint8",
            encoding="png",
            resolution=[1, 1, 1],
            voxel_offset=[0, 0, 0],
            chunk_size=[self.config.chunk_size, self.config.chunk_size, 1],
            volume_size=[width, height, 1],
        )

    def get_stats(self) -> Dict:
        """전체 통계 반환"""
        return {
            "cache": self.cache.get_stats(),
            "memory": self.monitor.get_cleanup_stats(),
            "config": {
                "chunk_size": self.config.chunk_size,
                "max_image_size_mb": self.config.max_image_size_mb,
                "cache_max_size_mb": self.config.cache_max_size_mb
            }
        }