import logging
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Union
from contextvars import ContextVar

# ✅ 현재 사용자 LoginId를 저장하는 context variable
current_user_context: ContextVar[Optional[str]] = ContextVar('current_user', default=None)


def set_current_user(login_id: str):
    """✅ 현재 요청의 사용자 LoginId 설정"""
    current_user_context.set(login_id)


def clear_current_user():
    """현재 요청의 사용자 정보 클리어"""
    current_user_context.set(None)


def get_current_user() -> Optional[str]:
    """✅ 현재 요청의 사용자 LoginId 가져오기"""
    return current_user_context.get()


class JsonFormatter(logging.Formatter):
    """
    로그를 JSON 라인 포맷으로 변환하는 포맷터
    """

    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "service": "viewer",
        }

        try:
            if isinstance(record.msg, str) and record.msg.startswith('{'):
                message_data = json.loads(record.msg)
                log_record.update(message_data)
            elif isinstance(record.msg, dict):
                log_record.update(record.msg)
            else:
                log_record["message"] = record.getMessage()
        except:
            log_record["message"] = record.getMessage()

        # ✅ [수정] 저장 시 호환성을 위해 user_id와 LoginId 모두 저장
        login_id = get_current_user()
        if login_id:
            log_record["user"] = login_id  # API 필터링용 표준 필드
            log_record["user_id"] = login_id  # 프론트엔드/필터링 표준
            log_record["LoginId"] = login_id  # 레거시 호환
            log_record["login_id"] = login_id  # 추가 안전장치

        return json.dumps(log_record, ensure_ascii=False)


def get_logger(service_name: str = "viewer", log_dir: str = "/logs"):
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    log_file = log_dir_path / str(now.year) / f"{now.month:02d}" / f"{now.day:02d}.txt"

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(console_handler)

    return logger


def parse_log_file(log_file_path: Path) -> List[Dict]:
    logs = []
    if not log_file_path.exists():
        return []

    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    log_entry = json.loads(line)
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error parsing log file: {e}")

    return sorted(logs, key=lambda x: x.get('timestamp', ''), reverse=True)


def filter_logs_by_user(logs: List[Dict], user_identifiers: Union[str, List[str]]) -> List[Dict]:
    """
    user_identifiers가 포함된 로그 필터링
    """
    if not user_identifiers:
        return logs

    if isinstance(user_identifiers, str):
        target_ids = {user_identifiers}
    else:
        target_ids = set(str(uid) for uid in user_identifiers if uid)

    filtered = []
    for log in logs:
        # ✅ [수정] 가능한 모든 키(user_id, LoginId, login_id)를 검사하여 하나라도 맞으면 통과
        log_user_id = str(log.get("user_id", ""))
        log_login_id = str(log.get("LoginId", ""))
        log_login_id_lower = str(log.get("login_id", ""))  # 소문자 키 추가 확인

        if (log_user_id in target_ids or
                log_login_id in target_ids or
                log_login_id_lower in target_ids):
            filtered.append(log)

    return filtered