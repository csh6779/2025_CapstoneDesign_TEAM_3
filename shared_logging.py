"""
통합 로깅 시스템
날짜별로 JSON 형식의 로그 파일 생성
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import traceback


class JSONFormatter(logging.Formatter):
    """JSON 형식의 로그 포맷터"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 추가 필드
        if hasattr(record, 'service'):
            log_data['service'] = record.service
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'extra_data'):
            log_data['extra_data'] = record.extra_data
        
        # 예외 정보
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data, ensure_ascii=False)


class DailyRotatingJSONLogger:
    """일별 로테이션 JSON 로거"""
    
    def __init__(self, service_name: str, log_base_dir: str = "/logs"):
        self.service_name = service_name
        self.log_base_dir = Path(log_base_dir)
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.DEBUG)
        
        # 기존 핸들러 제거
        self.logger.handlers.clear()
        
        # 현재 날짜
        self.current_date = None
        self.file_handler = None
        
        # 초기 설정
        self._setup_handler()
        
        # 콘솔 핸들러 추가 (일반 텍스트)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_handler(self):
        """날짜별 핸들러 설정"""
        now = datetime.now()
        today = now.date()
        
        if self.current_date != today:
            # 기존 핸들러 제거
            if self.file_handler:
                self.logger.removeHandler(self.file_handler)
                self.file_handler.close()
            
            # 새로운 로그 파일 경로
            year_dir = self.log_base_dir / str(now.year)
            month_dir = year_dir / f"{now.month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = month_dir / f"{now.day:02d}.txt"
            
            # 파일 핸들러 생성
            self.file_handler = logging.FileHandler(
                log_file, 
                mode='a', 
                encoding='utf-8'
            )
            self.file_handler.setLevel(logging.DEBUG)
            self.file_handler.setFormatter(JSONFormatter())
            
            self.logger.addHandler(self.file_handler)
            self.current_date = today
            
            print(f"📝 Log file: {log_file}")
    
    def _check_date_change(self):
        """날짜 변경 확인 및 핸들러 재설정"""
        if datetime.now().date() != self.current_date:
            self._setup_handler()
    
    def debug(self, message: str, **kwargs):
        """DEBUG 레벨 로그"""
        self._check_date_change()
        extra = self._make_extra(**kwargs)
        self.logger.debug(message, extra=extra)
    
    def info(self, message: str, **kwargs):
        """INFO 레벨 로그"""
        self._check_date_change()
        extra = self._make_extra(**kwargs)
        self.logger.info(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        """WARNING 레벨 로그"""
        self._check_date_change()
        extra = self._make_extra(**kwargs)
        self.logger.warning(message, extra=extra)
    
    def error(self, message: str, exc_info=None, **kwargs):
        """ERROR 레벨 로그"""
        self._check_date_change()
        extra = self._make_extra(**kwargs)
        self.logger.error(message, exc_info=exc_info, extra=extra)
    
    def critical(self, message: str, exc_info=None, **kwargs):
        """CRITICAL 레벨 로그"""
        self._check_date_change()
        extra = self._make_extra(**kwargs)
        self.logger.critical(message, exc_info=exc_info, extra=extra)
    
    def _make_extra(self, **kwargs) -> Dict[str, Any]:
        """추가 필드 생성"""
        extra = {'service': self.service_name}
        
        if kwargs:
            extra['extra_data'] = kwargs
        
        return extra


# 싱글톤 인스턴스
_loggers = {}


def get_logger(service_name: str, log_base_dir: str = "/logs") -> DailyRotatingJSONLogger:
    """로거 인스턴스 가져오기 (싱글톤)"""
    if service_name not in _loggers:
        _loggers[service_name] = DailyRotatingJSONLogger(service_name, log_base_dir)
    return _loggers[service_name]


# 사용 예시
if __name__ == "__main__":
    logger = get_logger("test_service", "./logs")
    
    logger.info("서비스 시작", version="1.0.0", port=8000)
    logger.debug("디버그 메시지", data={"key": "value"})
    logger.warning("경고 메시지", user_id="user123")
    
    try:
        raise ValueError("테스트 예외")
    except Exception as e:
        logger.error("에러 발생", exc_info=True, context="테스트")
