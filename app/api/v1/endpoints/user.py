# app/api/v1/endpoints/user.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.database import get_db
from app.repositories.user import UserRepository
from app.schemas.Users import UserCreate, UserUpdate, User as UserOut
from app.api.v1.deps.Auth import get_current_user, require_roles
from app.utils.json_logger import json_logger  # ✅ 변경됨: ncsa_logger → json_logger

router = APIRouter(prefix="/users", tags=["users"])
repo = UserRepository()


# 아이디 생성 (회원가입)
@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
        payload: UserCreate,
        request: Request,
        response: Response,
        db: Session = Depends(get_db)
):
    try:
        user = repo.create_user(db, payload=payload)

        # ✅ 제거됨: 사용자별 로그 디렉터리 생성 불필요
        # (날짜별 통합 로그 구조에서는 자동으로 날짜 폴더가 생성됨)

        # 회원가입 활동 로깅
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=user.UserName,
            activity_type="USER_REGISTER",
            details={
                "user_id": user.id,
                "login_id": user.LoginId,
                "role": user.Role
            }
        )

        json_logger.log_activity(
            username=user.UserName,
            activity="ACCOUNT_CREATED",
            status="SUCCESS",
            details={"login_id": user.LoginId, "role": user.Role}
        )

        return user

    except IntegrityError:
        # 실패 로그
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user="anonymous",  # ✅ 추가: 인증되지 않은 사용자
            activity_type="USER_REGISTER_FAILED",
            details={"reason": "duplicate_id"}
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 아이디 입니다."
        )


# 전체 유저를 보는건 admin만
@router.get("", response_model=list[UserOut])
async def list_users(
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        current_admin=Depends(require_roles("Admin", "admin"))
):
    users = repo.get_user(db)

    # 관리자 활동 로깅
    await json_logger.log_request(
        request=request,
        response=response,
        auth_user=current_admin.UserName,
        activity_type="ADMIN_LIST_USERS",
        details={"user_count": len(users)}
    )

    return users


# 내 정보 조회 -> 내 정보 수정 페이지에 매핑될 예정
@router.get("/me", response_model=UserOut)
async def read_me(
        request: Request,
        response: Response,
        current_user=Depends(get_current_user)
):
    # 내 정보 조회 로깅
    await json_logger.log_request(
        request=request,
        response=response,
        auth_user=current_user.UserName,
        activity_type="VIEW_PROFILE",
        details={"user_id": current_user.id}
    )

    return current_user


# 단건 조회
@router.get("/{Id}", response_model=UserOut)
async def read_user(
        Id: int,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    user = repo.get_user_by_id(db, Id)
    if not user:
        # 실패 로그
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="USER_NOT_FOUND",
            details={"target_id": Id}
        )
        raise HTTPException(status_code=404, detail="해당 유저를 찾지 못했습니다.")

    # 다른 사용자 정보 조회 로깅
    await json_logger.log_request(
        request=request,
        response=response,
        auth_user=current_user.UserName,
        activity_type="VIEW_USER",
        details={"target_user": user.UserName, "target_id": Id}
    )

    return user


# 내 정보 수정 -> 내 정보 수정에 매핑될 예정
@router.patch("/{Id}", response_model=UserOut)
async def update_user(
        Id: int,
        payload: UserUpdate,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    # 권한 체크: 자기 자신이거나 admin만 수정 가능
    if current_user.id != Id and current_user.Role not in ["Admin", "admin"]:
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="UNAUTHORIZED_UPDATE",
            details={"target_id": Id}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )

    user = repo.update_user(
        db, Id,
        UserName=payload.UserName,
        Role=payload.Role,
        UserImage=payload.UserImage,
        Password=payload.Password,
    )

    if not user:
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="UPDATE_USER_FAILED",
            details={"target_id": Id, "reason": "not_found"}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 유저를 찾지 못했습니다."
        )

    # 성공 로그
    await json_logger.log_request(
        request=request,
        response=response,
        auth_user=current_user.UserName,
        activity_type="UPDATE_USER",
        details={
            "target_user": user.UserName,
            "updated_fields": list(payload.model_dump(exclude_unset=True).keys())
        }
    )

    json_logger.log_activity(
        username=current_user.UserName,
        activity="PROFILE_UPDATED",
        status="SUCCESS",
        details={"user_id": Id}
    )

    return user


@router.delete("/{Id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
        Id: int,
        request: Request,
        response: Response,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    # 권한 체크: admin만 삭제 가능
    if current_user.Role not in ["Admin", "admin"]:
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="UNAUTHORIZED_DELETE",
            details={"target_id": Id}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="권한이 없습니다."
        )

    # 삭제 대상 사용자 정보 가져오기
    target_user = repo.get_user_by_id(db, Id)
    target_username = target_user.UserName if target_user else "unknown"

    ok = repo.delete_user(db, Id)
    if not ok:
        await json_logger.log_request(
            request=request,
            response=response,
            auth_user=current_user.UserName,
            activity_type="DELETE_USER_FAILED",
            details={"target_id": Id, "reason": "not_found"}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유저를 찾지 못했습니다."
        )

    # 성공 로그
    await json_logger.log_request(
        request=request,
        response=response,
        auth_user=current_user.UserName,
        activity_type="DELETE_USER",
        details={"target_user": target_username, "target_id": Id}
    )

    json_logger.log_activity(
        username=current_user.UserName,
        activity="USER_DELETED",
        status="SUCCESS",
        details={"deleted_user": target_username}
    )

    # 204는 바디 없이 반환
    return