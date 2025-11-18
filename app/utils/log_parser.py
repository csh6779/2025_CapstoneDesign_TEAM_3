# app/utils/log_parser.py
"""
로그 파일 파싱 유틸리티
JSON 로그 파일에서 사용자별 로그를 필터링하고 파싱합니다.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class LogParser:
    """JSON 로그 파일 파서"""
    
    def __init__(self, log_base_dir: str = "logs"):
        """
        Args:
            log_base_dir: 로그 디렉터리 기본 경로
        """
        self.log_base_dir = Path(log_base_dir)
    
    def get_available_dates(self) -> List[str]:
        """
        사용 가능한 로그 날짜 목록 반환
        
        Returns:
            날짜 목록 (YYYY-MM-DD 형식)
        """
        if not self.log_base_dir.exists():
            return []
        
        dates = []
        for item in self.log_base_dir.iterdir():
            if item.is_dir() and item.name.count('-') == 2:  # YYYY-MM-DD 형식
                try:
                    datetime.strptime(item.name, '%Y-%m-%d')
                    dates.append(item.name)
                except ValueError:
                    continue
        
        return sorted(dates, reverse=True)  # 최신 날짜부터
    
    def parse_log_file(self, file_path: Path) -> List[Dict]:
        """
        단일 로그 파일 파싱
        
        Args:
            file_path: 로그 파일 경로
            
        Returns:
            파싱된 로그 엔트리 리스트
        """
        logs = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        log_entry = json.loads(line)
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error parsing log file {file_path}: {e}")
        
        return logs
    
    def get_logs_by_date(self, date: str) -> List[Dict]:
        """
        특정 날짜의 모든 로그 조회
        
        Args:
            date: 날짜 (YYYY-MM-DD 형식)
            
        Returns:
            로그 엔트리 리스트
        """
        date_dir = self.log_base_dir / date
        if not date_dir.exists():
            return []
        
        all_logs = []
        for log_file in date_dir.glob("*.log"):
            logs = self.parse_log_file(log_file)
            all_logs.extend(logs)
        
        # 타임스탬프로 정렬
        all_logs.sort(key=lambda x: x.get('타임스탬프', ''))
        
        return all_logs
    
    def get_logs_by_user(
        self, 
        username: str, 
        date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        특정 사용자의 로그 조회
        
        Args:
            username: 사용자 이름
            date: 날짜 (YYYY-MM-DD 형식, None이면 모든 날짜)
            limit: 최대 반환 개수
            
        Returns:
            필터링된 로그 엔트리 리스트
        """
        if date:
            dates = [date]
        else:
            dates = self.get_available_dates()
        
        user_logs = []
        
        for log_date in dates:
            logs = self.get_logs_by_date(log_date)
            
            # 사용자 필터링
            for log in logs:
                if log.get('사용자') == username:
                    user_logs.append(log)
                    
                    if len(user_logs) >= limit:
                        break
            
            if len(user_logs) >= limit:
                break
        
        return user_logs[:limit]
    
    def get_logs_by_service(
        self,
        service: str,
        date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        특정 서비스의 로그 조회
        
        Args:
            service: 서비스 이름 (neuroglancer, api, fastapi 등)
            date: 날짜 (YYYY-MM-DD 형식)
            limit: 최대 반환 개수
            
        Returns:
            필터링된 로그 엔트리 리스트
        """
        if date:
            dates = [date]
        else:
            dates = self.get_available_dates()
        
        service_logs = []
        
        for log_date in dates:
            logs = self.get_logs_by_date(log_date)
            
            for log in logs:
                if log.get('서비스') == service:
                    service_logs.append(log)
                    
                    if len(service_logs) >= limit:
                        break
            
            if len(service_logs) >= limit:
                break
        
        return service_logs[:limit]
    
    def get_image_upload_logs(
        self,
        username: Optional[str] = None,
        date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        이미지 업로드 관련 로그만 조회
        
        Args:
            username: 사용자 이름 (None이면 모든 사용자)
            date: 날짜 (YYYY-MM-DD 형식)
            limit: 최대 반환 개수
            
        Returns:
            이미지 업로드 로그 리스트
        """
        if date:
            dates = [date]
        else:
            dates = self.get_available_dates()
        
        upload_logs = []
        
        for log_date in dates:
            logs = self.get_logs_by_date(log_date)
            
            for log in logs:
                # 이미지 업로드 관련 로그만 필터링
                message = log.get('메시지', '').lower()
                logger_name = log.get('로거', '').lower()
                
                is_upload = any([
                    'upload' in message,
                    'convert' in message,
                    '업로드' in message,
                    '변환' in message,
                    'neuroglancer' in logger_name
                ])
                
                if is_upload:
                    if username and log.get('사용자') != username:
                        continue
                    
                    upload_logs.append(log)
                    
                    if len(upload_logs) >= limit:
                        break
            
            if len(upload_logs) >= limit:
                break
        
        return upload_logs[:limit]
    
    def get_log_statistics(
        self,
        username: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict:
        """
        로그 통계 정보 조회
        
        Args:
            username: 사용자 이름 (None이면 전체)
            date: 날짜 (YYYY-MM-DD 형식)
            
        Returns:
            통계 정보 딕셔너리
        """
        if username:
            logs = self.get_logs_by_user(username, date, limit=10000)
        else:
            if date:
                logs = self.get_logs_by_date(date)
            else:
                logs = []
                for log_date in self.get_available_dates():
                    logs.extend(self.get_logs_by_date(log_date))
        
        # 로그 레벨별 카운트
        level_counts = {}
        service_counts = {}
        
        for log in logs:
            level = log.get('로그레벨', 'UNKNOWN')
            service = log.get('서비스', 'UNKNOWN')
            
            level_counts[level] = level_counts.get(level, 0) + 1
            service_counts[service] = service_counts.get(service, 0) + 1
        
        return {
            "total_logs": len(logs),
            "level_counts": level_counts,
            "service_counts": service_counts,
            "date_range": date if date else "all",
            "username": username if username else "all"
        }


# 싱글톤 인스턴스
log_parser = LogParser()
