# app/api/v1/endpoints/logs.py
"""
로그 관리 관련 API 엔드포인트
- NCSA Common Log Format 기반 로그 조회
- 사용자별 로그 파일 관리
- 로그 정리 및 분석
"""

from fastapi import APIRouter, Query, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import re

from app.api.v1.deps.Auth import get_current_user, require_roles
from app.utils.ncsa_logger import ncsa_logger

router = APIRouter()

# 로그 디렉터리
LOG_DIR = Path("logs")


@router.get("/logs/list")
async def list_log_files(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    로그 파일 목록 조회
    
    Returns:
        로그 파일 목록과 메타데이터
    """
    try:
        if not LOG_DIR.exists():
            return JSONResponse(content={
                "files": [],
                "count": 0,
                "message": "로그 디렉터리가 없습니다."
            })
        
        files = []
        
        # 공통 로그 파일들
        for log_file in sorted(LOG_DIR.glob("*.log")):
            stat = log_file.stat()
            files.append({
                "name": log_file.name,
                "type": "common",
                "size_bytes": stat.st_size,
                "size_mb": stat.st_size / 1024 / 1024,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        
        # 사용자별 로그 디렉터리 (관리자만)
        user_logs = []
        if current_user.Role in ["Admin", "admin"]:
            for user_dir in LOG_DIR.iterdir():
                if user_dir.is_dir():
                    activity_log = user_dir / "activity.log"
                    if activity_log.exists():
                        stat = activity_log.stat()
                        user_logs.append({
                            "username": user_dir.name,
                            "type": "user",
                            "size_bytes": stat.st_size,
                            "size_mb": stat.st_size / 1024 / 1024,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
                        })
        
        # 활동 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="LIST_LOGS",
            details={"common_files": len(files), "user_logs": len(user_logs)}
        )
        
        return JSONResponse(content={
            "common_files": files,
            "user_logs": user_logs,
            "total_count": len(files) + len(user_logs),
            "log_dir": str(LOG_DIR.absolute())
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 목록 조회 실패: {str(e)}")


@router.get("/logs/my-activities")
async def get_my_activities(
    request: Request,
    response: Response,
    lines: int = Query(100, ge=1, le=1000, description="읽을 줄 수 (1-1000)"),
    current_user=Depends(get_current_user)
):
    """
    내 활동 로그 조회
    
    Returns:
        현재 사용자의 최근 활동 로그
    """
    try:
        logs = ncsa_logger.get_user_logs(current_user.UserName, lines)
        
        # 로그 조회 활동 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VIEW_MY_LOGS",
            details={"lines_requested": lines, "lines_returned": len(logs)}
        )
        
        # NCSA 로그 파싱하여 구조화된 데이터로 변환
        parsed_logs = []
        ncsa_pattern = re.compile(
            r'([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+\[([^\]]+)\]\s+"([^"]+)"\s+(\d+)\s+([^\s]+)'
        )
        
        for log in logs:
            match = ncsa_pattern.match(log)
            if match:
                parsed_logs.append({
                    "remote_host": match.group(1),
                    "identity": match.group(2),
                    "user": match.group(3),
                    "timestamp": match.group(4),
                    "request": match.group(5),
                    "status": match.group(6),
                    "bytes": match.group(7),
                    "raw": log
                })
            else:
                parsed_logs.append({"raw": log})
        
        return JSONResponse(content={
            "username": current_user.UserName,
            "logs": parsed_logs,
            "total_lines": len(logs),
            "lines_requested": lines
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 읽기 실패: {str(e)}")


@router.get("/logs/user/{username}")
async def get_user_activities(
    username: str,
    request: Request,
    response: Response,
    lines: int = Query(100, ge=1, le=1000, description="읽을 줄 수 (1-1000)"),
    current_user=Depends(require_roles("Admin", "admin"))
):
    """
    특정 사용자의 활동 로그 조회 (관리자 전용)
    
    Returns:
        지정된 사용자의 최근 활동 로그
    """
    try:
        logs = ncsa_logger.get_user_logs(username, lines)
        
        if not logs:
            return JSONResponse(content={
                "username": username,
                "logs": [],
                "message": "해당 사용자의 로그를 찾을 수 없습니다."
            })
        
        # 관리자 활동 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="ADMIN_VIEW_USER_LOGS",
            details={"target_user": username, "lines": lines}
        )
        
        # NCSA 로그 파싱
        parsed_logs = []
        ncsa_pattern = re.compile(
            r'([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+\[([^\]]+)\]\s+"([^"]+)"\s+(\d+)\s+([^\s]+)'
        )
        
        for log in logs:
            match = ncsa_pattern.match(log)
            if match:
                parsed_logs.append({
                    "remote_host": match.group(1),
                    "identity": match.group(2),
                    "user": match.group(3),
                    "timestamp": match.group(4),
                    "request": match.group(5),
                    "status": match.group(6),
                    "bytes": match.group(7),
                    "raw": log
                })
            else:
                parsed_logs.append({"raw": log})
        
        return JSONResponse(content={
            "username": username,
            "logs": parsed_logs,
            "total_lines": len(logs),
            "lines_requested": lines
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 읽기 실패: {str(e)}")


@router.get("/logs/access")
async def get_access_logs(
    request: Request,
    response: Response,
    lines: int = Query(100, ge=1, le=1000, description="읽을 줄 수 (1-1000)"),
    current_user=Depends(require_roles("Admin", "admin"))
):
    """
    전체 액세스 로그 조회 (관리자 전용)
    
    Returns:
        NCSA Common Log Format의 액세스 로그
    """
    try:
        log_file = LOG_DIR / "access.log"
        
        if not log_file.exists():
            return JSONResponse(content={
                "logs": [],
                "message": "액세스 로그 파일이 없습니다."
            })
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]
        
        # 관리자 활동 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="ADMIN_VIEW_ACCESS_LOGS",
            details={"lines": lines}
        )
        
        # NCSA 로그 파싱
        parsed_logs = []
        ncsa_pattern = re.compile(
            r'([^\s]+)\s+([^\s]+)\s+([^\s]+)\s+\[([^\]]+)\]\s+"([^"]+)"\s+(\d+)\s+([^\s]+)(?:\s+"([^"]+)"\s+"([^"]+)")?'
        )
        
        for line in recent_lines:
            line = line.strip()
            match = ncsa_pattern.match(line)
            if match:
                parsed_logs.append({
                    "remote_host": match.group(1),
                    "identity": match.group(2),
                    "user": match.group(3),
                    "timestamp": match.group(4),
                    "request": match.group(5),
                    "status": match.group(6),
                    "bytes": match.group(7),
                    "referer": match.group(8) if match.group(8) else None,
                    "user_agent": match.group(9) if match.group(9) else None,
                    "raw": line
                })
            else:
                parsed_logs.append({"raw": line})
        
        return JSONResponse(content={
            "logs": parsed_logs,
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines),
            "log_file": log_file.name
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 읽기 실패: {str(e)}")


@router.get("/logs/stats")
async def get_log_stats(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    로그 통계 조회
    
    Returns:
        로그 파일별 통계 및 사용자 활동 통계
    """
    try:
        if not LOG_DIR.exists():
            return JSONResponse(content={
                "total_files": 0,
                "total_size_mb": 0,
                "log_types": {},
                "user_stats": {}
            })
        
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "common_logs": {},
            "user_stats": {}
        }
        
        # 공통 로그 파일 통계
        for log_file in LOG_DIR.glob("*.log"):
            stat = log_file.stat()
            
            # 파일 라인 수 계산
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f)
            except:
                line_count = 0
            
            stats["common_logs"][log_file.stem] = {
                "exists": True,
                "size_bytes": stat.st_size,
                "size_mb": stat.st_size / 1024 / 1024,
                "line_count": line_count,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
            stats["total_files"] += 1
            stats["total_size_bytes"] += stat.st_size
        
        # 사용자별 로그 통계 (본인 것만 또는 관리자는 전체)
        if current_user.Role in ["Admin", "admin"]:
            # 관리자는 모든 사용자 통계 조회
            for user_dir in LOG_DIR.iterdir():
                if user_dir.is_dir():
                    activity_log = user_dir / "activity.log"
                    if activity_log.exists():
                        stat = activity_log.stat()
                        try:
                            with open(activity_log, 'r', encoding='utf-8') as f:
                                line_count = sum(1 for _ in f)
                        except:
                            line_count = 0
                        
                        stats["user_stats"][user_dir.name] = {
                            "size_bytes": stat.st_size,
                            "size_mb": stat.st_size / 1024 / 1024,
                            "activity_count": line_count,
                            "last_activity": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        }
                        
                        stats["total_files"] += 1
                        stats["total_size_bytes"] += stat.st_size
        else:
            # 일반 사용자는 자신의 통계만
            user_log_dir = LOG_DIR / current_user.UserName
            if user_log_dir.exists():
                activity_log = user_log_dir / "activity.log"
                if activity_log.exists():
                    stat = activity_log.stat()
                    try:
                        with open(activity_log, 'r', encoding='utf-8') as f:
                            line_count = sum(1 for _ in f)
                    except:
                        line_count = 0
                    
                    stats["user_stats"][current_user.UserName] = {
                        "size_bytes": stat.st_size,
                        "size_mb": stat.st_size / 1024 / 1024,
                        "activity_count": line_count,
                        "last_activity": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
        
        stats["total_size_mb"] = stats["total_size_bytes"] / 1024 / 1024
        
        # 통계 조회 활동 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VIEW_LOG_STATS",
            details={"is_admin": current_user.Role in ["Admin", "admin"]}
        )
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 통계 조회 실패: {str(e)}")


@router.get("/logs/search")
async def search_logs(
    request: Request,
    response: Response,
    keyword: str = Query(..., description="검색 키워드"),
    log_type: str = Query("access", description="로그 유형 (access, user, all)"),
    max_results: int = Query(100, ge=1, le=1000, description="최대 결과 수"),
    current_user=Depends(get_current_user)
):
    """
    로그 검색
    
    Args:
        keyword: 검색 키워드
        log_type: 로그 유형 (access: 액세스 로그, user: 사용자 활동, all: 전체)
        max_results: 최대 결과 수
        
    Returns:
        검색 결과
    """
    try:
        results = []
        searched_files = []
        
        if log_type in ["access", "all"] and current_user.Role in ["Admin", "admin"]:
            # 액세스 로그 검색 (관리자만)
            log_file = LOG_DIR / "access.log"
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line_no, line in enumerate(f, 1):
                        if keyword.lower() in line.lower():
                            results.append({
                                "file": "access.log",
                                "line_number": line_no,
                                "content": line.strip()
                            })
                            if len(results) >= max_results:
                                break
                searched_files.append("access.log")
        
        if log_type in ["user", "all"]:
            # 사용자 활동 로그 검색
            if current_user.Role in ["Admin", "admin"]:
                # 관리자는 모든 사용자 로그 검색
                for user_dir in LOG_DIR.iterdir():
                    if user_dir.is_dir() and len(results) < max_results:
                        activity_log = user_dir / "activity.log"
                        if activity_log.exists():
                            with open(activity_log, 'r', encoding='utf-8') as f:
                                for line_no, line in enumerate(f, 1):
                                    if keyword.lower() in line.lower():
                                        results.append({
                                            "file": f"{user_dir.name}/activity.log",
                                            "line_number": line_no,
                                            "content": line.strip()
                                        })
                                        if len(results) >= max_results:
                                            break
                            searched_files.append(f"{user_dir.name}/activity.log")
            else:
                # 일반 사용자는 자신의 로그만 검색
                user_log = LOG_DIR / current_user.UserName / "activity.log"
                if user_log.exists():
                    with open(user_log, 'r', encoding='utf-8') as f:
                        for line_no, line in enumerate(f, 1):
                            if keyword.lower() in line.lower():
                                results.append({
                                    "file": f"{current_user.UserName}/activity.log",
                                    "line_number": line_no,
                                    "content": line.strip()
                                })
                                if len(results) >= max_results:
                                    break
                    searched_files.append(f"{current_user.UserName}/activity.log")
        
        # 검색 활동 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="SEARCH_LOGS",
            details={
                "keyword": keyword,
                "log_type": log_type,
                "results_found": len(results)
            }
        )
        
        return JSONResponse(content={
            "results": results,
            "count": len(results),
            "keyword": keyword,
            "log_type": log_type,
            "searched_files": searched_files,
            "max_results": max_results
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 검색 실패: {str(e)}")


@router.get("/logs/download/{username}")
async def download_user_log(
    username: str,
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    사용자 활동 로그 파일 다운로드
    
    Args:
        username: 사용자명
        
    Returns:
        로그 파일
    """
    try:
        # 권한 체크: 자신의 로그이거나 관리자
        if username != current_user.UserName and current_user.Role not in ["Admin", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="권한이 없습니다."
            )
        
        log_file = LOG_DIR / username / "activity.log"
        
        if not log_file.exists():
            raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다.")
        
        # 다운로드 활동 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="DOWNLOAD_LOG",
            details={"target_user": username}
        )
        
        return FileResponse(
            path=log_file,
            filename=f"{username}_activity.log",
            media_type='text/plain'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 다운로드 실패: {str(e)}")


@router.post("/logs/cleanup")
async def cleanup_old_logs(
    request: Request,
    response: Response,
    days: int = Query(30, ge=1, le=365, description="보관 일수 (1-365일)"),
    current_admin=Depends(require_roles("Admin", "admin"))
):
    """
    오래된 로그 파일 정리 (관리자 전용)
    
    Args:
        days: 보관할 일수 (기본 30일)
        
    Returns:
        삭제된 파일 정보
    """
    try:
        from datetime import datetime, timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        removed_files = []
        
        if not LOG_DIR.exists():
            return JSONResponse(content={
                "message": "로그 디렉터리가 없습니다.",
                "removed_count": 0,
                "removed_files": []
            })
        
        # 백업 파일 정리 (메인 로그 파일은 유지)
        for log_file in LOG_DIR.glob("*.log.*"):
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                try:
                    log_file.unlink()
                    removed_files.append({
                        "name": log_file.name,
                        "modified": mtime.isoformat()
                    })
                except Exception as e:
                    print(f"파일 삭제 실패: {log_file.name} - {e}")
        
        # 정리 활동 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_admin.UserName,
            activity_type="CLEANUP_LOGS",
            details={
                "days": days,
                "removed_count": len(removed_files)
            }
        )
        
        ncsa_logger.log_activity(
            username=current_admin.UserName,
            activity="LOGS_CLEANED",
            status="SUCCESS",
            details={
                "retention_days": days,
                "files_removed": len(removed_files)
            }
        )
        
        return JSONResponse(content={
            "message": f"{days}일 이상 경과한 로그 파일 정리 완료",
            "removed_count": len(removed_files),
            "removed_files": removed_files,
            "cutoff_date": cutoff.isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 정리 실패: {str(e)}")