# app/api/v1/endpoints/memory.py
"""
메모리 관리 관련 API 엔드포인트
- 메모리 상태 조회
- 캐시 정리
- 시스템 리소스 모니터링
"""

import os
import psutil
from fastapi import APIRouter, Request, Response, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.api.v1.deps.Auth import get_current_user
from app.utils.ncsa_logger import ncsa_logger

router = APIRouter()


def get_memory_info() -> Dict[str, Any]:
    """시스템 메모리 정보 조회"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    system_memory = psutil.virtual_memory()
    
    return {
        "process_mb": memory_info.rss / 1024 / 1024,  # 프로세스 메모리 (MB)
        "system_percent": system_memory.percent,  # 시스템 메모리 사용률 (%)
        "system_available_mb": system_memory.available / 1024 / 1024,  # 사용 가능 메모리 (MB)
        "system_total_mb": system_memory.total / 1024 / 1024  # 전체 메모리 (MB)
    }


@router.get("/memory-status")
async def get_memory_status(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    메모리 상태 조회
    
    - 프로세스 메모리 사용량
    - 시스템 메모리 사용률
    - 캐시 상태 (구현 시)
    """
    try:
        memory_info = get_memory_info()
        
        # 메모리 상태 조회 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VIEW_MEMORY_STATUS",
            details={
                "process_mb": round(memory_info["process_mb"], 2),
                "system_percent": round(memory_info["system_percent"], 1)
            }
        )
        
        return JSONResponse(content={
            "memory": memory_info,
            "cache": {
                "cache_size_mb": 0,  # TODO: 실제 캐시 크기 구현
                "cached_chunks": 0,  # TODO: 캐시된 청크 수 구현
                "hit_rate": 0.0  # TODO: 캐시 히트율 구현
            },
            "config": {
                "cache_max_size_mb": 200,  # 설정값
                "chunk_size": 512
            }
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/memory-cleanup")
async def memory_cleanup(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    강제 메모리 정리
    
    - 캐시 비우기
    - 가비지 컬렉션 실행
    """
    try:
        import gc
        
        # 가비지 컬렉션 실행
        freed_objects = gc.collect()
        
        # 메모리 정보 조회
        memory_after = get_memory_info()
        
        # 메모리 정리 활동 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="MEMORY_CLEANUP",
            details={
                "freed_objects": freed_objects,
                "memory_mb_after": round(memory_after["process_mb"], 2)
            }
        )
        
        ncsa_logger.log_activity(
            username=current_user.UserName,
            activity="MEMORY_CLEANED",
            status="SUCCESS",
            details={
                "freed_objects": freed_objects,
                "process_mb": round(memory_after["process_mb"], 2)
            }
        )
        
        return JSONResponse(content={
            "message": "메모리 정리 완료",
            "freed_objects": freed_objects,
            "freed_mb": 0,  # TODO: 실제 해제된 메모리 계산
            "memory_after": memory_after
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/system-info")
async def get_system_info(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    """
    시스템 정보 조회
    
    - CPU 사용률
    - 디스크 사용량
    - 프로세스 정보
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        disk_usage = psutil.disk_usage('/')
        process = psutil.Process(os.getpid())
        
        # 시스템 정보 조회 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VIEW_SYSTEM_INFO",
            details={
                "cpu_percent": cpu_percent,
                "disk_percent": disk_usage.percent
            }
        )
        
        return JSONResponse(content={
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "disk": {
                "total_gb": disk_usage.total / 1024 / 1024 / 1024,
                "used_gb": disk_usage.used / 1024 / 1024 / 1024,
                "free_gb": disk_usage.free / 1024 / 1024 / 1024,
                "percent": disk_usage.percent
            },
            "process": {
                "pid": process.pid,
                "threads": process.num_threads(),
                "cpu_percent": process.cpu_percent()
            },
            "memory": get_memory_info()
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )