# app/api/v1/endpoints/logs.py
"""
로그 관리 관련 API 엔드포인트 (날짜별 통합 로그 버전)
- 날짜별 통합 JSON 로그 조회
- 날짜 범위 기반 검색
- 사용자별 필터링
"""

from fastapi import APIRouter, Query, HTTPException, Depends, Request, Response, status
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pathlib import Path
from typing import Optional, List
from datetime import datetime, date, timedelta
import json
import zipfile
import io

from app.api.v1.deps.Auth import get_current_user, require_roles
from app.utils.json_logger import json_logger

router = APIRouter()

# 로그 디렉터리
LOG_DIR = Path("logs")


@router.get("/logs/dates")
async def list_log_dates(
        request: Request,
        response: Response,
        current_user=Depends(get_current_user)
):
    """
    로그가 존재하는 날짜 목록 조회

    Returns:
        날짜 목록 및 각 날짜별 기본 정보
    """
    try:
        dates = json_logger.get_available_dates()

        date_info = []
        for log_date in dates[:30]:  # 최근 30일만
            try:
                stats = json_logger.get_log_stats(datetime.fromisoformat(log_date).date())
                date_info.append({
                    "date": log_date,
                    "total_logs": stats.get("log_levels", {}).get("all", {}).get("line_count", 0),
                    "total_size_mb": stats.get("total_size_mb", 0),
                    "unique_users": stats.get("log_levels", {}).get("all", {}).get("unique_users", 0)
                })
            except:
                date_info.append({
                    "date": log_date,
                    "error": "통계 조회 실패"
                })

        # 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="LIST_LOG_DATES",
            details={"dates_count": len(dates)}
        )

        return JSONResponse(content={
            "dates": date_info,
            "total_dates": len(dates),
            "oldest_date": dates[-1] if dates else None,
            "newest_date": dates[0] if dates else None
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"날짜 목록 조회 실패: {str(e)}")


@router.get("/logs/date/{log_date}")
async def get_logs_by_date(
        log_date: str,
        request: Request,
        response: Response,
        log_level: Optional[str] = Query(None, description="로그 레벨 필터"),
        username: Optional[str] = Query(None, description="사용자 필터"),
        lines: Optional[int] = Query(None, ge=1, le=10000, description="조회할 줄 수"),
        current_user=Depends(get_current_user)
):
    """
    특정 날짜의 로그 조회

    Args:
        log_date: 날짜 (YYYY-MM-DD 형식)
        log_level: 로그 레벨 필터 (선택)
        username: 사용자 필터 (선택)
        lines: 최대 줄 수 (선택)

    Returns:
        해당 날짜의 로그
    """
    try:
        # 날짜 파싱
        try:
            target_date = datetime.strptime(log_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요.")

        # 권한 체크: 다른 사용자 필터는 관리자만
        if username and username != current_user.UserName:
            if current_user.Role not in ["Admin", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="다른 사용자의 로그를 조회할 권한이 없습니다."
                )

        # 일반 사용자는 자신의 로그만
        if current_user.Role not in ["Admin", "admin"]:
            username = current_user.UserName

        # 로그 조회
        logs = json_logger.get_logs_by_date(
            log_date=target_date,
            log_level=log_level,
            username=username,
            lines=lines
        )

        # 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VIEW_DATE_LOGS",
            details={
                "target_date": log_date,
                "log_level": log_level,
                "username_filter": username,
                "results": len(logs)
            }
        )

        return JSONResponse(content={
            "date": log_date,
            "log_level": log_level,
            "username": username,
            "logs": logs,
            "count": len(logs),
            "format": "JSON"
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 조회 실패: {str(e)}")


@router.get("/logs/my-activities")
async def get_my_activities(
        request: Request,
        response: Response,
        days: int = Query(7, ge=1, le=30, description="조회할 일 수 (1-30)"),
        log_level: Optional[str] = Query(None, description="로그 레벨 필터"),
        max_results: int = Query(100, ge=1, le=1000, description="최대 결과 수"),
        current_user=Depends(get_current_user)
):
    """
    내 활동 로그 조회 (최근 N일)

    Args:
        days: 조회할 일 수
        log_level: 로그 레벨 필터
        max_results: 최대 결과 수

    Returns:
        현재 사용자의 최근 활동 로그
    """
    try:
        logs = json_logger.get_user_logs(
            username=current_user.UserName,
            days=days,
            log_level=log_level,
            max_results=max_results
        )

        # 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VIEW_MY_LOGS",
            details={
                "days": days,
                "log_level": log_level,
                "results": len(logs)
            }
        )

        return JSONResponse(content={
            "username": current_user.UserName,
            "days": days,
            "log_level": log_level,
            "logs": logs,
            "count": len(logs),
            "format": "JSON"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 조회 실패: {str(e)}")


@router.get("/logs/user/{username}")
async def get_user_activities(
        username: str,
        request: Request,
        response: Response,
        days: int = Query(7, ge=1, le=30, description="조회할 일 수"),
        log_level: Optional[str] = Query(None, description="로그 레벨 필터"),
        max_results: int = Query(100, ge=1, le=1000, description="최대 결과 수"),
        current_user=Depends(require_roles("Admin", "admin"))
):
    """
    특정 사용자의 활동 로그 조회 (관리자 전용)

    Args:
        username: 사용자명
        days: 조회할 일 수
        log_level: 로그 레벨 필터
        max_results: 최대 결과 수

    Returns:
        지정된 사용자의 최근 활동 로그
    """
    try:
        logs = json_logger.get_user_logs(
            username=username,
            days=days,
            log_level=log_level,
            max_results=max_results
        )

        if not logs:
            return JSONResponse(content={
                "username": username,
                "logs": [],
                "message": "해당 사용자의 로그를 찾을 수 없습니다."
            })

        # 관리자 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="ADMIN_VIEW_USER_LOGS",
            details={
                "target_user": username,
                "days": days,
                "log_level": log_level,
                "results": len(logs)
            }
        )

        return JSONResponse(content={
            "username": username,
            "days": days,
            "log_level": log_level,
            "logs": logs,
            "count": len(logs),
            "format": "JSON"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 조회 실패: {str(e)}")


@router.get("/logs/stats")
async def get_log_stats(
        request: Request,
        response: Response,
        log_date: Optional[str] = Query(None, description="통계를 볼 날짜 (YYYY-MM-DD)"),
        current_user=Depends(get_current_user)
):
    """
    로그 통계 조회

    Args:
        log_date: 통계를 볼 날짜 (None이면 오늘)

    Returns:
        로그 파일별 통계
    """
    try:
        # 날짜 파싱
        target_date = None
        if log_date:
            try:
                target_date = datetime.strptime(log_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다.")

        stats = json_logger.get_log_stats(target_date)

        # 일반 사용자는 자신의 통계만 표시
        if current_user.Role not in ["Admin", "admin"]:
            user_counts = stats.get("user_counts", {})
            stats["user_counts"] = {
                current_user.UserName: user_counts.get(current_user.UserName, 0)
            }

        # 통계 조회 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="VIEW_LOG_STATS",
            details={
                "target_date": log_date or date.today().isoformat(),
                "is_admin": current_user.Role in ["Admin", "admin"]
            }
        )

        return JSONResponse(content=stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 통계 조회 실패: {str(e)}")


@router.get("/logs/search")
async def search_logs(
        request: Request,
        response: Response,
        keyword: str = Query(..., description="검색 키워드"),
        start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
        log_level: Optional[str] = Query(None, description="로그 레벨 필터"),
        username: Optional[str] = Query(None, description="사용자 필터 (관리자 전용)"),
        max_results: int = Query(100, ge=1, le=1000, description="최대 결과 수"),
        current_user=Depends(get_current_user)
):
    """
    로그 검색

    Args:
        keyword: 검색 키워드
        start_date: 시작 날짜 (선택)
        end_date: 종료 날짜 (선택)
        log_level: 로그 레벨 필터
        username: 사용자 필터 (관리자만)
        max_results: 최대 결과 수

    Returns:
        검색 결과
    """
    try:
        # 권한 체크
        if username and username != current_user.UserName:
            if current_user.Role not in ["Admin", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="다른 사용자의 로그를 검색할 권한이 없습니다."
                )

        # 일반 사용자는 자신의 로그만
        if current_user.Role not in ["Admin", "admin"]:
            username = current_user.UserName

        # 날짜 파싱
        parsed_start_date = None
        parsed_end_date = None

        if start_date:
            try:
                parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="시작 날짜 형식이 잘못되었습니다.")

        if end_date:
            try:
                parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="종료 날짜 형식이 잘못되었습니다.")

        # 검색 실행
        results = json_logger.search_logs(
            keyword=keyword,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            log_level=log_level,
            username=username,
            max_results=max_results
        )

        # 검색 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="SEARCH_LOGS",
            details={
                "keyword": keyword,
                "start_date": start_date,
                "end_date": end_date,
                "log_level": log_level,
                "username": username,
                "results_found": len(results)
            }
        )

        return JSONResponse(content={
            "results": results,
            "count": len(results),
            "keyword": keyword,
            "date_range": {
                "start": start_date or (date.today() - timedelta(days=7)).isoformat(),
                "end": end_date or date.today().isoformat()
            },
            "log_level": log_level,
            "username": username,
            "max_results": max_results,
            "format": "JSON"
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 검색 실패: {str(e)}")


@router.get("/logs/download")
async def download_logs(
        request: Request,
        response: Response,
        log_date: str = Query(..., description="다운로드할 날짜 (YYYY-MM-DD)"),
        log_level: Optional[str] = Query(None, description="로그 레벨 (None이면 all.log)"),
        current_user=Depends(get_current_user)
):
    """
    특정 날짜의 로그 파일 다운로드

    Args:
        log_date: 날짜
        log_level: 로그 레벨 (선택)

    Returns:
        로그 파일
    """
    try:
        # 권한 체크: 관리자만
        if current_user.Role not in ["Admin", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="로그 다운로드는 관리자만 가능합니다."
            )

        # 날짜 파싱
        try:
            target_date = datetime.strptime(log_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다.")

        # 로그 파일 경로
        if log_level:
            log_file = LOG_DIR / log_date / f"{log_level.lower()}.log"
            filename = f"{log_date}_{log_level.lower()}.log"
        else:
            log_file = LOG_DIR / log_date / "all.log"
            filename = f"{log_date}_all.log"

        if not log_file.exists():
            raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다.")

        # 다운로드 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="DOWNLOAD_LOG",
            details={"log_date": log_date, "log_level": log_level}
        )

        return FileResponse(
            path=log_file,
            filename=filename,
            media_type='application/json'
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 다운로드 실패: {str(e)}")


@router.get("/logs/download-range")
async def download_logs_range(
        request: Request,
        response: Response,
        start_date: str = Query(..., description="시작 날짜 (YYYY-MM-DD)"),
        end_date: str = Query(..., description="종료 날짜 (YYYY-MM-DD)"),
        current_user=Depends(require_roles("Admin", "admin"))
):
    """
    날짜 범위의 로그를 ZIP 파일로 다운로드 (관리자 전용)

    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜

    Returns:
        ZIP 파일
    """
    try:
        # 날짜 파싱
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="잘못된 날짜 형식입니다.")

        if parsed_start > parsed_end:
            raise HTTPException(status_code=400, detail="시작 날짜가 종료 날짜보다 늦습니다.")

        # 날짜 범위 제한 (최대 7일)
        if (parsed_end - parsed_start).days > 7:
            raise HTTPException(status_code=400, detail="최대 7일 범위까지만 다운로드 가능합니다.")

        # ZIP 파일 생성
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            current_date = parsed_start

            while current_date <= parsed_end:
                date_str = current_date.isoformat()
                date_dir = LOG_DIR / date_str

                if date_dir.exists():
                    # 해당 날짜의 모든 로그 파일 추가
                    for log_file in date_dir.glob("*.log"):
                        arcname = f"{date_str}/{log_file.name}"
                        zip_file.write(log_file, arcname)

                current_date += timedelta(days=1)

        # 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="DOWNLOAD_LOG_RANGE",
            details={"start_date": start_date, "end_date": end_date}
        )

        zip_buffer.seek(0)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename=logs_{start_date}_to_{end_date}.zip"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 다운로드 실패: {str(e)}")


@router.post("/logs/cleanup")
async def cleanup_old_logs(
        request: Request,
        response: Response,
        retention_days: int = Query(30, ge=1, le=365, description="보관 일수 (1-365일)"),
        current_admin=Depends(require_roles("Admin", "admin"))
):
    """
    오래된 로그 정리 (관리자 전용)

    Args:
        retention_days: 보관할 일수 (기본 30일)

    Returns:
        삭제된 날짜 정보
    """
    try:
        result = json_logger.cleanup_old_logs(retention_days)

        # 정리 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_admin.UserName,
            activity_type="CLEANUP_LOGS",
            details={
                "retention_days": retention_days,
                "removed_count": result["removed_count"],
                "removed_size_mb": result["removed_size_mb"]
            }
        )

        json_logger.log_activity(
            username=current_admin.UserName,
            activity="LOGS_CLEANED",
            status="SUCCESS",
            details=result
        )

        return JSONResponse(content={
            "message": f"{retention_days}일 이상 경과한 로그 정리 완료",
            **result
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 정리 실패: {str(e)}")