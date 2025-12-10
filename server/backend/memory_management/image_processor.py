import asyncio
import os
import json
from pathlib import Path
from typing import AsyncGenerator, Tuple, Dict
from PIL import Image
import numpy as np

from .memory_config import MemoryConfig, ProcessingResult
from .memory_monitor import MemoryMonitor
from .chunk_cache import ChunkCache


class MemoryEfficientProcessor:
    """메모리 효율적 이미지 처리 - Neuroglancer chunk key format 수정된 버전"""

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
        
        print(f"이미지 처리 시작: {image_path} -> {volume_path}")
        
        try:
            # 이미지 메타데이터 로드
            is_valid, meta = await self.validate_image_size(image_path)
            if not is_valid:
                error_msg = f"이미지 검증 실패: {meta.get('error', 'Size too large')}"
                print(error_msg)
                yield ProcessingResult(
                    chunk_x=0, chunk_y=0, progress=0,
                    memory_usage=self.monitor.get_memory_usage(),
                    cache_size_mb=self.cache.current_size_mb,
                    success=False,
                    error_message=error_msg
                )
                return

            width, height, channels = meta["width"], meta["height"], meta["channels"]
            print(f"이미지 정보: {width}x{height}, {channels} channels, {meta['mode']} mode")

            # 볼륨 디렉터리 생성
            os.makedirs(volume_path, exist_ok=True)
            
            # info 파일 생성 (Neuroglancer 형식)
            info = self._create_neuroglancer_info(width, height, channels)
            info_path = os.path.join(volume_path, "info")
            with open(info_path, 'w') as f:
                json.dump(info, f, indent=2)
            print(f"info 파일 생성됨: {info_path}")

            # 청크 처리
            chunk_count = 0
            async for result in self._process_chunks_simple(image_path, volume_path, width, height, meta["mode"]):
                if result.success:
                    chunk_count += 1
                print(f"청크 처리: ({result.chunk_x}, {result.chunk_y}) - {'성공' if result.success else '실패'}")
                yield result
                
            print(f"이미지 처리 완료: 총 {chunk_count}개 청크")

        except Exception as e:
            error_msg = f"처리 중 오류 발생: {str(e)}"
            print(error_msg)
            yield ProcessingResult(
                chunk_x=0, chunk_y=0, progress=0,
                memory_usage=self.monitor.get_memory_usage(),
                cache_size_mb=self.cache.current_size_mb,
                success=False,
                error_message=error_msg
            )

    async def _process_chunks_simple(self, image_path: str, volume_path: str,
                                   width: int, height: int, mode: str) -> AsyncGenerator[ProcessingResult, None]:
        """단순화된 청크 처리"""
        
        chunk_size = self.config.chunk_size
        chunks_x = (width + chunk_size - 1) // chunk_size
        chunks_y = (height + chunk_size - 1) // chunk_size
        total_chunks = chunks_x * chunks_y

        print(f"청크 처리 시작: {chunks_x}x{chunks_y} = {total_chunks}개 청크")

        # 이미지를 한 번만 로드
        try:
            with Image.open(image_path) as img:
                if mode in ['RGBA', 'P']:
                    img = img.convert('RGB')
                img_array = np.array(img)
                
            print(f"이미지 배열 크기: {img_array.shape}")
            
        except Exception as e:
            yield ProcessingResult(
                chunk_x=0, chunk_y=0, progress=0,
                memory_usage=self.monitor.get_memory_usage(),
                cache_size_mb=self.cache.current_size_mb,
                success=False,
                error_message=f"이미지 로드 실패: {str(e)}"
            )
            return

        processed_chunks = 0
        for chunk_y in range(chunks_y):
            for chunk_x in range(chunks_x):
                try:
                    # 청크 영역 계산
                    x_start = chunk_x * chunk_size
                    y_start = chunk_y * chunk_size
                    x_end = min(x_start + chunk_size, width)
                    y_end = min(y_start + chunk_size, height)
                    
                    # 청크 추출
                    chunk_data = img_array[y_start:y_end, x_start:x_end]
                    
                    # 올바른 Neuroglancer chunk key format으로 저장
                    success = await self._save_chunk_neuroglancer_format(
                        chunk_data, volume_path, x_start, x_end, y_start, y_end, 0, 1
                    )
                    
                    processed_chunks += 1
                    progress = (processed_chunks / total_chunks) * 100

                    yield ProcessingResult(
                        chunk_x=chunk_x,
                        chunk_y=chunk_y,
                        progress=progress,
                        memory_usage=self.monitor.get_memory_usage(),
                        cache_size_mb=self.cache.current_size_mb,
                        success=success,
                        error_message=None if success else f"청크 저장 실패: ({chunk_x}, {chunk_y})"
                    )

                    print(f"청크 성공: ({chunk_x}, {chunk_y}) - 진행률: {progress:.1f}%")

                except Exception as e:
                    processed_chunks += 1
                    progress = (processed_chunks / total_chunks) * 100
                    
                    yield ProcessingResult(
                        chunk_x=chunk_x,
                        chunk_y=chunk_y,
                        progress=progress,
                        memory_usage=self.monitor.get_memory_usage(),
                        cache_size_mb=self.cache.current_size_mb,
                        success=False,
                        error_message=f"청크 처리 실패 ({chunk_x}, {chunk_y}): {str(e)}"
                    )

    async def _save_chunk_neuroglancer_format(self, chunk_data: np.ndarray, volume_path: str,
                                            x_start: int, x_end: int, y_start: int, y_end: int,
                                            z_start: int, z_end: int) -> bool:
        """
        Neuroglancer chunk key format으로 저장
        Format: {x_start}-{x_end}_{y_start}-{y_end}_{z_start}-{z_end}
        """
        try:
            # Neuroglancer chunk key format
            chunk_key = f"{x_start}-{x_end}_{y_start}-{y_end}_{z_start}-{z_end}"
            chunk_path = os.path.join(volume_path, chunk_key)
            
            # PIL Image로 변환하여 저장
            if len(chunk_data.shape) == 2:
                # 그레이스케일
                chunk_img = Image.fromarray(chunk_data, mode='L')
            else:
                # RGB
                chunk_img = Image.fromarray(chunk_data, mode='RGB')
            
            chunk_img.save(chunk_path, format='PNG')
            print(f"청크 저장 완료: {chunk_key}")
            return True
            
        except Exception as e:
            print(f"PNG 저장 실패 ({x_start}-{x_end}_{y_start}-{y_end}): {e}")
            return False

    def _create_neuroglancer_info(self, width: int, height: int, channels: int) -> dict:
        """Neuroglancer info 파일 생성"""
        
        chunk_size = self.config.chunk_size
        
        return {
            "data_type": "uint8",
            "num_channels": channels,
            "scales": [
                {
                    "chunk_sizes": [[chunk_size, chunk_size, 1]],
                    "encoding": "png",
                    "key": "",
                    "resolution": [1, 1, 1],
                    "size": [width, height, 1],
                    "voxel_offset": [0, 0, 0]
                }
            ],
            "type": "image"
        }

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
