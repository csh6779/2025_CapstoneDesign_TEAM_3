"""사용자 관리 API (JSON 기반)"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from core.Jwt import get_current_user, require_admin
from repositories.json_user_repository import JSONUserRepository, UserDict
from schemas.Users import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["사용자"])

user_repo = JSONUserRepository()

@router.get("/me", response_model=UserResponse)
async def get_my_info(current_user: UserDict = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 조회"""
    return current_user

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: UserDict = Depends(get_current_user)
):
    """특정 사용자 정보 조회 (본인 또는 관리자만)"""
    # 본인이거나 관리자인 경우만 허용
    if current_user.id != user_id and current_user.Role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없습니다."
        )
    
    user = user_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    return user

@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: UserDict = Depends(require_admin)
):
    """모든 사용자 조회 (관리자만)"""
    users = user_repo.get_users(skip, limit)
    return users

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: UserDict = Depends(get_current_user)
):
    """사용자 정보 수정 (본인만)"""
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인의 정보만 수정할 수 있습니다."
        )
    
    updated_user = user_repo.update_user(user_id, payload)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    return updated_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: UserDict = Depends(require_admin)
):
    """사용자 삭제 (관리자만)"""
    success = user_repo.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다."
        )
    
    return None
