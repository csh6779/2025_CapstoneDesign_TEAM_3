"""이미지 로그 API (파일 기반 수정버전)"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

# ✅ 모듈 경로 확보 (Docker 환경 고려)
current_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# ✅ shared_logging에서 파일 파싱 함수 가져오기
try:
    from shared_logging import parse_log_file, filter_logs_by_user
except ImportError:
    # 경로 문제 발생 시 폴백
    sys.path.append("/viewer")
    from shared_logging import parse_log_file, filter_logs_by_user

from database.database import get_db
from core.Jwt import get_current_user
from core.UserModel import User

router = APIRouter(prefix="/image-logs", tags=["이미지 로그"])

# ✅ 로그 파일이 저장되는 실제 위치
LOG_DIR = "/logs"

@router.get("/me")
async def get_my_logs(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = Query(None, description="조회 시작 날짜"),
    end_date: Optional[date] = Query(None, description="조회 종료 날짜"),
    level: Optional[str] = Query(None, description="로그 레벨 필터 (INFO, WARNING, ERROR)"), # ✅ 레벨 파라미터 추가
    current_user: User = Depends(get_current_user)
):
    """
    내 로그 목록 조회 (DB가 아닌 /logs 디렉토리의 텍스트 파일 조회)
    """
    # 1. 사용자 식별 (LoginId 와 DB ID 모두 사용)
    user_identifiers = [current_user.LoginId, str(current_user.id)]

    # 2. 날짜 범위 설정 (기본값: 최근 7일)
    if not end_date:
        end_date = datetime.now().date()
    if not start_date:
        # 기본적으로 일주일 치 로그 스캔
        start_date = end_date - timedelta(days=7)

    all_logs = []
    log_base = Path(LOG_DIR)

    # 3. 날짜별 파일 순회
    current_date = start_date
    while current_date <= end_date:
        log_file = (
            log_base
            / str(current_date.year)
            / f"{current_date.month:02d}"
            / f"{current_date.day:02d}.txt"
        )

        if log_file.exists():
            try:
                logs = parse_log_file(log_file)
                all_logs.extend(logs)
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")

        current_date += timedelta(days=1)

    # 4. 사용자 필터링
    user_logs = filter_logs_by_user(all_logs, user_identifiers)

    # ✅ 5. 로그 레벨 필터링 (추가된 로직)
    if level:
        target_level = level.upper()
        user_logs = [log for log in user_logs if log.get("level") == target_level]

    # 6. 최신순 정렬
    user_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # 7. 페이징 처리
    if limit > 0:
        paged_logs = user_logs[skip : skip + limit]
    else:
        paged_logs = user_logs[skip:]

    return paged_logs


@router.get("/all")
async def get_all_logs(
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[date] = Query(None, description="조회 시작 날짜"),
        end_date: Optional[date] = Query(None, description="조회 종료 날짜"),
        level: Optional[str] = Query(None, description="로그 레벨 (INFO, WARNING, ERROR)"),
        target_user_id: Optional[str] = Query(None, description="특정 사용자 ID 필터링"),  # ✅ 사용자 필터 추가
        current_user: User = Depends(get_current_user)
):
    """
    [관리자 전용] 모든 사용자의 로그 조회
    """
    # 1. 권한 체크 (관리자만 허용)
    if current_user.Role != 'admin':
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    # 2. 날짜 범위 설정
    if not end_date:
        end_date = datetime.now().date()
    if not start_date:
        start_date = end_date - timedelta(days=7)

    all_logs = []
    log_base = Path(LOG_DIR)

    # 3. 날짜별 파일 순회
    current_date = start_date
    while current_date <= end_date:
        log_file = (
                log_base
                / str(current_date.year)
                / f"{current_date.month:02d}"
                / f"{current_date.day:02d}.txt"
        )

        if log_file.exists():
            try:
                logs = parse_log_file(log_file)
                all_logs.extend(logs)
            except Exception as e:
                print(f"Error reading log file {log_file}: {e}")

        current_date += timedelta(days=1)

    # 4. 필터링
    filtered_logs = all_logs

    # 4-1. 특정 사용자 필터링 (target_user_id가 있을 때만)
    if target_user_id:
        # 입력받은 ID가 LoginId일 수도 있고 숫자 ID일 수도 있음 -> 둘 다 체크하도록 shared_logging 수정 필요하나,
        # 일단 여기서는 입력된 값 그대로 필터링 시도
        filtered_logs = filter_logs_by_user(all_logs, target_user_id)

    # 4-2. 로그 레벨 필터링
    if level:
        target_level = level.upper()
        filtered_logs = [log for log in filtered_logs if log.get("level") == target_level]

    # 5. 최신순 정렬
    filtered_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # 6. 페이징 처리
    if limit > 0:
        paged_logs = filtered_logs[skip: skip + limit]
    else:
        paged_logs = filtered_logs[skip:]

    return paged_logs