# app/utils/json_logger.py
"""
JSON 형식 구조화된 로거 (날짜 계층 구조 버전)
- 디렉토리 구조: /logs/년도/월/일.txt (예: /logs/2025/11/11.txt)
- 날짜가 바뀌면 자동으로 새 파일 생성
- 모든 로그 레벨을 하나의 파일에 통합 기록
- 로그 레벨: DEBUG, INFO, WARNING, ERROR, CRITICAL
"""

import json
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from threading import current_thread
import asyncio
from fastapi import Request, Response


class JSONLogger:
    """JSON 형식으로 로그를 기록하는 로거 (날짜 계층 구조)"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 로그 레벨
        self.LOG_LEVELS = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }

    def _get_date_log_path(self, log_date: Optional[date] = None) -> Path:
        """
        날짜별 로그 파일 경로 반환: /logs/년도/월/일.txt

        Args:
            log_date: 로그 날짜 (None이면 오늘)

        Returns:
            로그 파일 경로 (예: logs/2025/11/11.txt)
        """
        if log_date is None:
            log_date = date.today()

        # 년도/월 디렉터리 생성: logs/2025/11/
        year_dir = self.log_dir / str(log_date.year)
        month_dir = year_dir / f"{log_date.month:02d}"
        month_dir.mkdir(parents=True, exist_ok=True)

        # 일.txt 파일: logs/2025/11/11.txt
        return month_dir / f"{log_date.day:02d}.txt"

    def _write_log(self, log_entry: Dict[str, Any], log_file: Path):
        """로그 항목을 JSON 형식으로 파일에 기록"""
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"로그 기록 실패: {e}")

    def create_log_entry(
            self,
            username: str,
            log_level: str = "INFO",
            message: str = "",
            logger_name: str = "system",
            service: str = "api",
            additional_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        구조화된 JSON 로그 항목 생성

        Args:
            username: 사용자명 또는 시스템
            log_level: DEBUG, INFO, WARNING, ERROR, CRITICAL
            message: 로그 메시지
            logger_name: 로거 이름 (모듈/컴포넌트 식별)
            service: 서비스 이름
            additional_info: 추가 정보 딕셔너리

        Returns:
            JSON 로그 항목
        """
        now = datetime.now()

        log_entry = {
            "timestamp": now.isoformat(),
            "date": now.date().isoformat(),
            "time": now.strftime("%H:%M:%S"),
            "username": username,
            "log_level": log_level.upper(),
            "message": message,
            "logger": logger_name,
            "thread": current_thread().name,
            "service": service
        }

        # 추가 정보가 있으면 병합
        if additional_info:
            log_entry["details"] = additional_info

        return log_entry

    def log(
            self,
            username: str,
            log_level: str = "INFO",
            message: str = "",
            logger_name: str = "system",
            service: str = "api",
            additional_info: Optional[Dict[str, Any]] = None
    ):
        """
        로그 기록 (날짜 계층 구조)

        Args:
            username: 사용자명
            log_level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: 로그 메시지
            logger_name: 로거 이름
            service: 서비스 이름
            additional_info: 추가 정보
        """
        log_entry = self.create_log_entry(
            username=username,
            log_level=log_level,
            message=message,
            logger_name=logger_name,
            service=service,
            additional_info=additional_info
        )

        # 오늘 날짜 기준으로 로그 파일 결정
        # 날짜가 바뀌면 자동으로 새 파일 생성됨
        log_file = self._get_date_log_path()
        self._write_log(log_entry, log_file)

    async def log_request(
            self,
            request: Request,
            response: Response,
            auth_user: str,
            activity_type: str,
            details: Optional[Dict[str, Any]] = None
    ):
        """
        HTTP 요청 로깅

        Args:
            request: FastAPI Request 객체
            response: FastAPI Response 객체
            auth_user: 인증된 사용자명
            activity_type: 활동 유형
            details: 추가 상세 정보
        """
        # 요청 정보 수집
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "client_host": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "activity_type": activity_type
        }

        # 추가 상세 정보 병합
        if details:
            request_info.update(details)

        # 상태 코드 확인
        status_code = getattr(response, "status_code", 200)

        # 로그 레벨 결정
        if status_code >= 500:
            log_level = "ERROR"
        elif status_code >= 400:
            log_level = "WARNING"
        else:
            log_level = "INFO"

        # 로그 메시지 생성
        message = f"{request.method} {request.url.path} - {activity_type} - {status_code}"

        # 로그 기록
        self.log(
            username=auth_user,
            log_level=log_level,
            message=message,
            logger_name="api.request",
            service="fastapi",
            additional_info={
                "request": request_info,
                "status_code": status_code
            }
        )

    def log_activity(
            self,
            username: str,
            activity: str,
            status: str = "SUCCESS",
            details: Optional[Dict[str, Any]] = None
    ):
        """
        사용자 활동 로깅

        Args:
            username: 사용자명
            activity: 활동 내용
            status: 상태 (SUCCESS, FAILED, WARNING)
            details: 추가 상세 정보
        """
        log_level = "ERROR" if status == "FAILED" else "INFO"

        self.log(
            username=username,
            log_level=log_level,
            message=f"{activity} - {status}",
            logger_name="activity",
            service="user_activity",
            additional_info={
                "activity": activity,
                "status": status,
                **(details or {})
            }
        )

    def get_logs_by_date(
            self,
            log_date: date,
            log_level: Optional[str] = None,
            username: Optional[str] = None,
            lines: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        특정 날짜의 로그 조회

        Args:
            log_date: 조회할 날짜
            log_level: 로그 레벨 필터 (선택)
            username: 사용자 필터 (선택)
            lines: 조회할 줄 수 (선택, None이면 전체)

        Returns:
            파싱된 JSON 로그 리스트
        """
        log_file = self._get_date_log_path(log_date)

        if not log_file.exists():
            return []

        logs = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

                # lines 제한이 있으면 최근 N개만
                if lines:
                    all_lines = all_lines[-lines:]

                for line in all_lines:
                    try:
                        log_entry = json.loads(line.strip())

                        # 로그 레벨 필터링
                        if log_level and log_entry.get("log_level") != log_level.upper():
                            continue

                        # 사용자 필터링
                        if username and log_entry.get("username") != username:
                            continue

                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        # JSON 파싱 실패 시 원본 텍스트로 저장
                        logs.append({"raw": line.strip(), "parse_error": True})
        except Exception as e:
            print(f"로그 읽기 실패: {e}")

        return logs

    def get_logs_by_date_range(
            self,
            start_date: date,
            end_date: date,
            log_level: Optional[str] = None,
            username: Optional[str] = None,
            max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        날짜 범위의 로그 조회

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            log_level: 로그 레벨 필터
            username: 사용자 필터
            max_results: 최대 결과 수

        Returns:
            파싱된 JSON 로그 리스트
        """
        all_logs = []
        current_date = start_date

        while current_date <= end_date and len(all_logs) < max_results:
            date_logs = self.get_logs_by_date(
                log_date=current_date,
                log_level=log_level,
                username=username
            )
            all_logs.extend(date_logs)

            # 다음 날짜
            from datetime import timedelta
            current_date += timedelta(days=1)

            if len(all_logs) >= max_results:
                break

        return all_logs[:max_results]

    def get_user_logs(
            self,
            username: str,
            days: int = 7,
            log_level: Optional[str] = None,
            max_results: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        특정 사용자의 로그 조회 (최근 N일)

        Args:
            username: 사용자명
            days: 조회할 일 수 (기본 7일)
            log_level: 로그 레벨 필터
            max_results: 최대 결과 수

        Returns:
            파싱된 JSON 로그 리스트
        """
        from datetime import timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        return self.get_logs_by_date_range(
            start_date=start_date,
            end_date=end_date,
            log_level=log_level,
            username=username,
            max_results=max_results
        )

    def search_logs(
            self,
            keyword: str,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            log_level: Optional[str] = None,
            username: Optional[str] = None,
            max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        로그 검색

        Args:
            keyword: 검색 키워드
            start_date: 시작 날짜 (None이면 7일 전)
            end_date: 종료 날짜 (None이면 오늘)
            log_level: 로그 레벨 필터
            username: 사용자 필터
            max_results: 최대 결과 수

        Returns:
            검색된 로그 리스트
        """
        from datetime import timedelta

        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=7)

        # 날짜 범위의 로그 가져오기
        logs = self.get_logs_by_date_range(
            start_date=start_date,
            end_date=end_date,
            log_level=log_level,
            username=username,
            max_results=max_results * 2  # 검색 여유분
        )

        # 키워드 검색
        results = []
        keyword_lower = keyword.lower()

        for log in logs:
            if len(results) >= max_results:
                break

            # JSON 전체를 문자열로 변환하여 검색
            log_str = json.dumps(log, ensure_ascii=False).lower()
            if keyword_lower in log_str:
                results.append(log)

        return results

    def get_available_dates(self) -> List[str]:
        """
        로그가 존재하는 날짜 목록 반환

        Returns:
            날짜 리스트 (ISO 형식)
        """
        dates = []

        if not self.log_dir.exists():
            return dates

        # /logs/년도/ 디렉터리 순회
        for year_dir in sorted(self.log_dir.iterdir(), reverse=True):
            if not year_dir.is_dir():
                continue

            # /logs/년도/월/ 디렉터리 순회
            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir():
                    continue

                # /logs/년도/월/일.txt 파일 찾기
                for day_file in sorted(month_dir.glob("*.txt"), reverse=True):
                    try:
                        year = year_dir.name
                        month = month_dir.name
                        day = day_file.stem  # .txt 제거

                        # YYYY-MM-DD 형식으로 변환
                        date_str = f"{year}-{month}-{day}"
                        datetime.fromisoformat(date_str)  # 유효성 검증
                        dates.append(date_str)
                    except ValueError:
                        continue

        return dates

    def get_log_stats(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        로그 통계 조회

        Args:
            target_date: 대상 날짜 (None이면 오늘)

        Returns:
            로그 파일 통계
        """
        if target_date is None:
            target_date = date.today()

        log_file = self._get_date_log_path(target_date)

        if not log_file.exists():
            return {
                "date": target_date.isoformat(),
                "exists": False,
                "message": "해당 날짜의 로그가 없습니다."
            }

        stats = {
            "date": target_date.isoformat(),
            "exists": True,
            "file_path": str(log_file),
            "file_size_bytes": 0,
            "file_size_mb": 0,
            "total_lines": 0,
            "log_level_counts": {
                "DEBUG": 0,
                "INFO": 0,
                "WARNING": 0,
                "ERROR": 0,
                "CRITICAL": 0
            },
            "user_counts": {},
            "activity_counts": {}
        }

        try:
            # 파일 크기
            file_stat = log_file.stat()
            stats["file_size_bytes"] = file_stat.st_size
            stats["file_size_mb"] = round(file_stat.st_size / 1024 / 1024, 2)
            stats["modified"] = datetime.fromtimestamp(file_stat.st_mtime).isoformat()

            # 로그 내용 분석
            from collections import Counter
            user_counter = Counter()
            activity_counter = Counter()

            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    stats["total_lines"] += 1

                    try:
                        log = json.loads(line.strip())

                        # 로그 레벨 집계
                        level = log.get("log_level", "INFO")
                        if level in stats["log_level_counts"]:
                            stats["log_level_counts"][level] += 1

                        # 사용자 집계
                        username = log.get("username", "unknown")
                        user_counter[username] += 1

                        # 활동 집계
                        if "details" in log and isinstance(log["details"], dict):
                            activity = log["details"].get("activity_type") or log["details"].get("activity")
                            if activity:
                                activity_counter[activity] += 1
                    except json.JSONDecodeError:
                        continue

            stats["user_counts"] = dict(user_counter.most_common(20))
            stats["activity_counts"] = dict(activity_counter.most_common(20))
            stats["unique_users"] = len(user_counter)

        except Exception as e:
            stats["error"] = str(e)

        return stats

    def cleanup_old_logs(self, retention_days: int = 30) -> Dict[str, Any]:
        """
        오래된 로그 삭제

        Args:
            retention_days: 보관 일수

        Returns:
            삭제 결과
        """
        from datetime import timedelta

        cutoff_date = date.today() - timedelta(days=retention_days)
        removed_files = []
        removed_size = 0

        if not self.log_dir.exists():
            return {
                "removed_files": [],
                "removed_count": 0,
                "removed_size_mb": 0,
                "cutoff_date": cutoff_date.isoformat()
            }

        # /logs/년도/ 디렉터리 순회
        for year_dir in self.log_dir.iterdir():
            if not year_dir.is_dir():
                continue

            # /logs/년도/월/ 디렉터리 순회
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue

                # /logs/년도/월/일.txt 파일 찾기
                for day_file in month_dir.glob("*.txt"):
                    try:
                        year = year_dir.name
                        month = month_dir.name
                        day = day_file.stem

                        file_date = date(int(year), int(month), int(day))

                        if file_date < cutoff_date:
                            file_size = day_file.stat().st_size
                            day_file.unlink()
                            removed_files.append(f"{year}/{month}/{day}.txt")
                            removed_size += file_size
                    except (ValueError, OSError) as e:
                        print(f"파일 처리 실패: {day_file} - {e}")
                        continue

                # 빈 월 디렉터리 삭제
                if not list(month_dir.iterdir()):
                    month_dir.rmdir()

            # 빈 년도 디렉터리 삭제
            if not list(year_dir.iterdir()):
                year_dir.rmdir()

        return {
            "removed_files": removed_files,
            "removed_count": len(removed_files),
            "removed_size_bytes": removed_size,
            "removed_size_mb": round(removed_size / 1024 / 1024, 2),
            "cutoff_date": cutoff_date.isoformat()
        }


# 싱글톤 인스턴스
json_logger = JSONLogger()