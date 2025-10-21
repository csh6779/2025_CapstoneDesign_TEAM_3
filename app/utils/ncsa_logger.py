# app/utils/ncsa_logger.py
"""
NCSA Common Log Format 로깅 시스템
Format: remote_host identity auth_user [date] "method url protocol" status bytes
Example: 127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326
"""

import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import Request, Response
import time

class NCSALogger:
    """NCSA Common Log Format 로거"""
    
    def __init__(self, log_dir: str = "logs"):
        """
        Args:
            log_dir: 로그 디렉터리 경로
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 공통 로그 파일
        self.access_log = self._setup_logger("access", "access.log")
        
        # 사용자별 로거 캐시
        self._user_loggers: Dict[str, logging.Logger] = {}
    
    def _setup_logger(self, name: str, filename: str, user_dir: Optional[str] = None) -> logging.Logger:
        """로거 설정"""
        if user_dir:
            log_path = self.log_dir / user_dir / filename
            log_path.parent.mkdir(parents=True, exist_ok=True)
            logger_name = f"{name}_{user_dir}"
        else:
            log_path = self.log_dir / filename
            logger_name = name
        
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        
        # 기존 핸들러 제거
        logger.handlers = []
        
        # 파일 핸들러 추가
        handler = logging.FileHandler(log_path, encoding='utf-8')
        # NCSA 형식은 포맷터 없이 직접 메시지로 기록
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)
        
        return logger
    
    def get_user_logger(self, username: str) -> logging.Logger:
        """사용자별 로거 가져오기 또는 생성"""
        if username not in self._user_loggers:
            self._user_loggers[username] = self._setup_logger(
                f"user_{username}", 
                "activity.log", 
                username
            )
        return self._user_loggers[username]
    
    def create_user_log_dir(self, username: str):
        """사용자 로그 디렉터리 생성 (회원가입 시)"""
        user_log_dir = self.log_dir / username
        user_log_dir.mkdir(parents=True, exist_ok=True)
        
        # 초기 로그 파일 생성
        initial_log = user_log_dir / "activity.log"
        if not initial_log.exists():
            initial_log.touch()
            
        # 사용자 생성 이벤트 로깅
        logger = self.get_user_logger(username)
        timestamp = datetime.now(timezone.utc).strftime('%d/%b/%Y:%H:%M:%S %z')
        log_entry = f'- - {username} [{timestamp}] "USER_CREATED /users/register HTTP/1.1" 201 -'
        logger.info(log_entry)
    
    def format_ncsa_log(
        self,
        remote_host: str,
        identity: str = "-",
        auth_user: str = "-",
        timestamp: Optional[str] = None,
        method: str = "GET",
        url: str = "/",
        protocol: str = "HTTP/1.1",
        status: int = 200,
        bytes_sent: int = 0,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None
    ) -> str:
        """NCSA Common Log Format 또는 Combined Log Format 생성"""
        
        if not timestamp:
            timestamp = datetime.now(timezone.utc).strftime('%d/%b/%Y:%H:%M:%S %z')
        
        # 기본 NCSA format
        log_entry = f'{remote_host} {identity} {auth_user} [{timestamp}] "{method} {url} {protocol}" {status} {bytes_sent if bytes_sent > 0 else "-"}'
        
        # Combined Log Format (optional)
        if user_agent or referer:
            referer = referer or "-"
            user_agent = user_agent or "-"
            log_entry += f' "{referer}" "{user_agent}"'
        
        return log_entry
    
    async def log_request(
        self,
        request: Request,
        response: Response,
        auth_user: Optional[str] = None,
        process_time: Optional[float] = None,
        activity_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """HTTP 요청 로깅"""
        
        # 클라이언트 정보 추출
        remote_host = request.client.host if request.client else "unknown"
        method = request.method
        url = str(request.url.path)
        if request.url.query:
            url += f"?{request.url.query}"
        
        # 헤더 정보
        user_agent = request.headers.get("user-agent", "-")
        referer = request.headers.get("referer", "-")
        
        # 응답 정보
        status = response.status_code
        bytes_sent = int(response.headers.get("content-length", 0))
        
        # NCSA 로그 생성
        log_entry = self.format_ncsa_log(
            remote_host=remote_host,
            auth_user=auth_user or "-",
            method=method,
            url=url,
            status=status,
            bytes_sent=bytes_sent,
            user_agent=user_agent,
            referer=referer
        )
        
        # 공통 액세스 로그에 기록
        self.access_log.info(log_entry)
        
        # 사용자별 로그에 기록
        if auth_user and auth_user != "-":
            user_logger = self.get_user_logger(auth_user)
            
            # 활동 타입별 추가 정보
            if activity_type:
                timestamp = datetime.now(timezone.utc).strftime('%d/%b/%Y:%H:%M:%S %z')
                
                # 활동별 상세 로그
                if activity_type == "CHUNK_SPLIT":
                    detail_msg = f'- - {auth_user} [{timestamp}] "ACTIVITY chunk_split {details.get("volume_name", "unknown")} chunks={details.get("chunk_count", 0)}" 200 -'
                
                elif activity_type == "IMAGE_VIEW":
                    detail_msg = f'- - {auth_user} [{timestamp}] "ACTIVITY image_view {details.get("image_name", "unknown")} size={details.get("size", 0)}" 200 -'
                
                elif activity_type == "VOLUME_UPLOAD":
                    detail_msg = f'- - {auth_user} [{timestamp}] "ACTIVITY volume_upload {details.get("volume_name", "unknown")} size={details.get("file_size", 0)}" 200 -'
                
                elif activity_type == "VOLUME_DELETE":
                    detail_msg = f'- - {auth_user} [{timestamp}] "ACTIVITY volume_delete {details.get("volume_name", "unknown")}" 200 -'
                
                elif activity_type == "LOGIN":
                    detail_msg = f'- - {auth_user} [{timestamp}] "ACTIVITY login success from={remote_host}" 200 -'
                
                elif activity_type == "LOGOUT":
                    detail_msg = f'- - {auth_user} [{timestamp}] "ACTIVITY logout from={remote_host}" 200 -'
                
                else:
                    detail_msg = f'- - {auth_user} [{timestamp}] "ACTIVITY {activity_type} {details or ""}" 200 -'
                
                user_logger.info(detail_msg)
            
            # 기본 요청도 사용자 로그에 기록
            user_logger.info(log_entry)
    
    def log_activity(
        self,
        username: str,
        activity: str,
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None
    ):
        """사용자 활동 로깅 (수동)"""
        
        if not username:
            return
        
        logger = self.get_user_logger(username)
        timestamp = datetime.now(timezone.utc).strftime('%d/%b/%Y:%H:%M:%S %z')
        
        # 상세 정보 포맷팅
        detail_str = ""
        if details:
            detail_str = " ".join([f"{k}={v}" for k, v in details.items()])
        
        log_entry = f'- - {username} [{timestamp}] "ACTIVITY {activity} {status}" {detail_str}'
        logger.info(log_entry)
    
    def get_user_logs(self, username: str, lines: int = 100) -> list:
        """사용자 로그 읽기"""
        user_log_file = self.log_dir / username / "activity.log"
        
        if not user_log_file.exists():
            return []
        
        try:
            with open(user_log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                return [line.strip() for line in all_lines[-lines:]]
        except Exception:
            return []


# 프로젝트 루트 경로 계산 (app/utils/ncsa_logger.py -> 프로젝트 루트)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = PROJECT_ROOT / "logs"

# 싱글톤 인스턴스 - 프로젝트 루트의 logs 디렉터리 사용
ncsa_logger = NCSALogger(log_dir=str(LOG_DIR))


# FastAPI 미들웨어용 함수
async def log_request_middleware(request: Request, call_next):
    """FastAPI 미들웨어로 사용할 함수"""
    start_time = time.time()
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = time.time() - start_time
    
    # 사용자 정보 추출 (JWT 토큰에서)
    auth_user = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from app.api.v1.deps.Auth import decode_token
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            auth_user = payload.get("username") or payload.get("sub")
        except:
            pass
    
    # 로그 기록
    await ncsa_logger.log_request(
        request=request,
        response=response,
        auth_user=auth_user,
        process_time=process_time
    )
    
    return response
