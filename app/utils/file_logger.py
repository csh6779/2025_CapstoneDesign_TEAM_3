# app/utils/file_logger.py
"""
파일 기반 로깅 시스템
- 다양한 레벨의 로거 (main, error, performance, debug)
- 파일 크기 기반 로테이션
- 일별 로테이션 지원
"""

import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List


class FileLogger:
    """파일 기반 로깅 시스템"""

    def __init__(
            self,
            log_dir: str = "logs",
            log_prefix: str = "app",
            max_bytes: int = 10 * 1024 * 1024,  # 10MB
            backup_count: int = 5,
            enable_daily_rotation: bool = True,
            enable_console: bool = False
    ):
        """
        Args:
            log_dir: 로그 파일이 저장될 디렉터리
            log_prefix: 로그 파일 이름 접두사
            max_bytes: 파일당 최대 크기
            backup_count: 백업 파일 개수
            enable_daily_rotation: 일별 로테이션 활성화
            enable_console: 콘솔 출력 활성화
        """
        self.log_dir = Path(log_dir)
        self.log_prefix = log_prefix
        self.enable_console = enable_console

        # 로그 디렉터리 생성
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 로거 설정
        self.setup_loggers(max_bytes, backup_count, enable_daily_rotation)

    def setup_loggers(self, max_bytes: int, backup_count: int, enable_daily_rotation: bool):
        """다양한 로거 설정"""

        # 1. 메인 로거 (모든 로그)
        self.main_logger = self._create_logger(
            "MainLogger",
            self.log_dir / f"{self.log_prefix}_main.log",
            logging.INFO,
            max_bytes,
            backup_count
        )

        # 2. 에러 로거 (에러만)
        self.error_logger = self._create_logger(
            "ErrorLogger",
            self.log_dir / f"{self.log_prefix}_error.log",
            logging.ERROR,
            max_bytes,
            backup_count
        )

        # 3. 성능 로거 (성능 메트릭만)
        self.performance_logger = self._create_logger(
            "PerformanceLogger",
            self.log_dir / f"{self.log_prefix}_performance.log",
            logging.INFO,
            max_bytes,
            backup_count,
            separate_format=True
        )

        # 4. 디버그 로거 (상세 디버그 정보)
        self.debug_logger = self._create_logger(
            "DebugLogger",
            self.log_dir / f"{self.log_prefix}_debug.log",
            logging.DEBUG,
            max_bytes,
            backup_count
        )

        # 5. 일별 로거 (날짜별 로그)
        if enable_daily_rotation:
            self.daily_logger = self._create_daily_logger(
                "DailyLogger",
                self.log_dir / f"{self.log_prefix}_daily.log",
                backup_count
            )
        else:
            self.daily_logger = None

    def _create_logger(
            self,
            name: str,
            filepath: Path,
            level: int,
            max_bytes: int,
            backup_count: int,
            separate_format: bool = False
    ) -> logging.Logger:
        """개별 로거 생성"""
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # 기존 핸들러 제거
        logger.handlers.clear()

        # 파일 핸들러 (크기 기반 로테이션)
        file_handler = RotatingFileHandler(
            filepath,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)

        # 포맷 설정
        if separate_format:
            # 성능 로그용 간단한 포맷
            formatter = logging.Formatter(
                '%(asctime)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            # 일반 로그용 상세 포맷
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 콘솔 출력 (선택적)
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        logger.propagate = False  # 부모 로거로 전파 방지

        return logger

    def _create_daily_logger(
            self,
            name: str,
            filepath: Path,
            backup_count: int
    ) -> logging.Logger:
        """일별 로테이션 로거 생성"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        # 일별 로테이션 핸들러
        file_handler = TimedRotatingFileHandler(
            filepath,
            when='midnight',
            interval=1,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.suffix = "%Y%m%d"  # 백업 파일명에 날짜 추가

        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.propagate = False

        return logger

    # === 로깅 메서드 ===

    def info(self, message: str):
        """INFO 레벨 로그"""
        self.main_logger.info(message)
        if self.daily_logger:
            self.daily_logger.info(message)

    def debug(self, message: str):
        """DEBUG 레벨 로그"""
        self.main_logger.debug(message)
        self.debug_logger.debug(message)

    def warning(self, message: str):
        """WARNING 레벨 로그"""
        self.main_logger.warning(message)
        if self.daily_logger:
            self.daily_logger.warning(message)

    def error(self, message: str, exc_info=None):
        """ERROR 레벨 로그"""
        self.main_logger.error(message, exc_info=exc_info)
        self.error_logger.error(message, exc_info=exc_info)
        if self.daily_logger:
            self.daily_logger.error(message, exc_info=exc_info)

    def performance(self, message: str):
        """성능 메트릭 로그"""
        self.performance_logger.info(message)

    def log_separator(self, char: str = "=", length: int = 80):
        """구분선 추가"""
        separator = char * length
        self.main_logger.info(separator)
        if self.daily_logger:
            self.daily_logger.info(separator)

    def log_header(self, title: str):
        """헤더 추가"""
        self.log_separator("=")
        self.info(f" {title} ")
        self.log_separator("=")

    def log_section(self, title: str):
        """섹션 구분"""
        self.log_separator("-", 60)
        self.info(f"[ {title} ]")
        self.log_separator("-", 60)

    # === API 요청 로깅 ===

    def log_request(self, method: str, path: str, client_ip: str = None):
        """API 요청 로그"""
        client_info = f" from {client_ip}" if client_ip else ""
        self.info(f"→ {method} {path}{client_info}")

    def log_response(self, method: str, path: str, status_code: int, duration_ms: float):
        """API 응답 로그"""
        status_icon = "✓" if 200 <= status_code < 300 else "✗"
        self.info(f"← {status_icon} {method} {path} - {status_code} ({duration_ms:.2f}ms)")
        self.performance(f"{method} | {path} | {status_code} | {duration_ms:.2f}ms")

    def log_upload(self, filename: str, size_mb: float, duration_sec: float):
        """파일 업로드 로그"""
        speed = size_mb / duration_sec if duration_sec > 0 else 0
        self.info(f"📤 업로드: {filename} ({size_mb:.2f} MB, {duration_sec:.2f}초, {speed:.2f} MB/s)")
        self.performance(f"UPLOAD | {filename} | {size_mb:.2f} MB | {duration_sec:.2f}s | {speed:.2f} MB/s")

    def log_conversion(self, volume_name: str, duration_sec: float, chunk_count: int):
        """이미지 변환 로그"""
        self.info(f"🔄 변환: {volume_name} ({duration_sec:.2f}초, {chunk_count}개 청크)")
        self.performance(f"CONVERSION | {volume_name} | {duration_sec:.2f}s | {chunk_count} chunks")

    def log_memory(self, event: str, before_mb: float, after_mb: float):
        """메모리 이벤트 로그"""
        delta = after_mb - before_mb
        self.info(f"💾 {event}: {after_mb:.2f} MB (변화: {delta:+.2f} MB)")
        self.performance(f"MEMORY | {event} | Before: {before_mb:.2f} | After: {after_mb:.2f} | Delta: {delta:+.2f}")

    # === 파일 관리 ===

    def get_log_files(self) -> List[Path]:
        """로그 파일 목록 반환"""
        return list(self.log_dir.glob(f"{self.log_prefix}*.log"))

    def get_file_size(self, filepath: Path) -> str:
        """파일 크기 반환 (human-readable)"""
        size = filepath.stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    def list_logs(self):
        """로그 파일 목록 출력"""
        files = self.get_log_files()
        self.info(f"\n로그 파일 목록 ({len(files)}개):")
        for f in sorted(files):
            size = self.get_file_size(f)
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            self.info(f"  - {f.name} ({size}) - 수정: {mtime}")

    def cleanup_old_logs(self, days: int = 7) -> int:
        """오래된 로그 파일 삭제"""
        cutoff = datetime.now() - timedelta(days=days)

        removed = 0
        for f in self.get_log_files():
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                try:
                    f.unlink()
                    removed += 1
                    self.info(f"삭제된 로그: {f.name}")
                except Exception as e:
                    self.error(f"로그 삭제 실패: {f.name} - {e}")

        self.info(f"총 {removed}개의 오래된 로그 파일 삭제됨")
        return removed

    def get_recent_logs(self, log_type: str = "main", lines: int = 100) -> List[str]:
        """최근 로그 읽기"""
        log_file = self.log_dir / f"{self.log_prefix}_{log_type}.log"
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return [line.strip() for line in all_lines[-lines:]]
        except Exception as e:
            self.error(f"로그 읽기 실패: {e}")
            return []
