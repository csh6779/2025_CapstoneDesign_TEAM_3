# app/api/v1/endpoints/logs.py
"""
로그 관리 관련 API 엔드포인트
- 로그 조회
- 로그 파일 관리
- 로그 정리
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from typing import Optional, List
from datetime import datetime

router = APIRouter()

# 로그 디렉터리
LOG_DIR = Path("logs")


@router.get("/logs/list")
def list_log_files():
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
        for log_file in sorted(LOG_DIR.glob("*.log")):
            stat = log_file.stat()
            files.append({
                "name": log_file.name,
                "size_bytes": stat.st_size,
                "size_mb": stat.st_size / 1024 / 1024,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        
        return JSONResponse(content={
            "files": files,
            "count": len(files),
            "log_dir": str(LOG_DIR.absolute())
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 목록 조회 실패: {str(e)}")


@router.get("/logs/recent")
def get_recent_logs(
    log_type: str = Query("main", description="로그 유형 (main, error, performance, debug, daily)"),
    lines: int = Query(100, ge=1, le=1000, description="읽을 줄 수 (1-1000)")
):
    """
    최근 로그 조회
    
    Args:
        log_type: 로그 유형 (main, error, performance, debug, daily)
        lines: 읽을 줄 수
        
    Returns:
        최근 로그 라인들
    """
    try:
        log_file = LOG_DIR / f"app_{log_type}.log"
        
        if not log_file.exists():
            return JSONResponse(content={
                "logs": [],
                "total_lines": 0,
                "returned_lines": 0,
                "log_type": log_type,
                "message": f"로그 파일을 찾을 수 없습니다: {log_file.name}"
            })
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]
        
        return JSONResponse(content={
            "logs": [line.strip() for line in recent_lines],
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines),
            "log_type": log_type,
            "log_file": log_file.name
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 읽기 실패: {str(e)}")


@router.get("/logs/download/{log_type}")
def download_log_file(log_type: str):
    """
    로그 파일 다운로드
    
    Args:
        log_type: 로그 유형
        
    Returns:
        로그 파일
    """
    try:
        log_file = LOG_DIR / f"app_{log_type}.log"
        
        if not log_file.exists():
            raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다.")
        
        return FileResponse(
            path=log_file,
            filename=log_file.name,
            media_type='text/plain'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 다운로드 실패: {str(e)}")


@router.post("/logs/cleanup")
def cleanup_old_logs(days: int = Query(7, ge=1, le=365, description="보관 일수 (1-365일)")):
    """
    오래된 로그 파일 정리
    
    Args:
        days: 보관할 일수 (기본 7일)
        
    Returns:
        삭제된 파일 수
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
        
        for log_file in LOG_DIR.glob("*.log*"):
            # 메인 로그 파일은 제외 (백업 파일만 삭제)
            if not any(log_file.name.endswith(f"_{t}.log") for t in ["main", "error", "performance", "debug", "daily"]):
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
        
        return JSONResponse(content={
            "message": f"{days}일 이상 경과한 로그 파일 정리 완료",
            "removed_count": len(removed_files),
            "removed_files": removed_files,
            "cutoff_date": cutoff.isoformat()
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 정리 실패: {str(e)}")


@router.get("/logs/stats")
def get_log_stats():
    """
    로그 통계 조회
    
    Returns:
        로그 파일별 통계
    """
    try:
        if not LOG_DIR.exists():
            return JSONResponse(content={
                "total_files": 0,
                "total_size_mb": 0,
                "log_types": {}
            })
        
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "log_types": {}
        }
        
        for log_type in ["main", "error", "performance", "debug", "daily"]:
            log_file = LOG_DIR / f"app_{log_type}.log"
            if log_file.exists():
                stat = log_file.stat()
                
                # 파일 라인 수 계산
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        line_count = sum(1 for _ in f)
                except:
                    line_count = 0
                
                stats["log_types"][log_type] = {
                    "exists": True,
                    "size_bytes": stat.st_size,
                    "size_mb": stat.st_size / 1024 / 1024,
                    "line_count": line_count,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
                
                stats["total_files"] += 1
                stats["total_size_bytes"] += stat.st_size
            else:
                stats["log_types"][log_type] = {
                    "exists": False
                }
        
        stats["total_size_mb"] = stats["total_size_bytes"] / 1024 / 1024
        
        return JSONResponse(content=stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 통계 조회 실패: {str(e)}")


@router.get("/logs/search")
def search_logs(
    log_type: str = Query("main", description="로그 유형"),
    keyword: str = Query(..., description="검색 키워드"),
    max_results: int = Query(100, ge=1, le=1000, description="최대 결과 수")
):
    """
    로그 검색
    
    Args:
        log_type: 로그 유형
        keyword: 검색 키워드
        max_results: 최대 결과 수
        
    Returns:
        검색 결과
    """
    try:
        log_file = LOG_DIR / f"app_{log_type}.log"
        
        if not log_file.exists():
            return JSONResponse(content={
                "results": [],
                "count": 0,
                "keyword": keyword,
                "message": "로그 파일을 찾을 수 없습니다."
            })
        
        results = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, 1):
                if keyword.lower() in line.lower():
                    results.append({
                        "line_number": line_no,
                        "content": line.strip()
                    })
                    if len(results) >= max_results:
                        break
        
        return JSONResponse(content={
            "results": results,
            "count": len(results),
            "keyword": keyword,
            "log_type": log_type,
            "max_results": max_results
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 검색 실패: {str(e)}")
