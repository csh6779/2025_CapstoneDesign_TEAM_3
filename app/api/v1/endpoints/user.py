# app/api/v1/endpoints/user.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from app.schemas.Users import User, UserCreate, UserUpdate
from app.repositories.user import UserRepository
from app.database.database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# Repository 인스턴스를 얻기 위한 의존성 함수
def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Repository 인스턴스를 제공하는 의존성 주입 함수"""
    return UserRepository(db)

# [C] Create - POST /v1/users
@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    repo: UserRepository = Depends(get_user_repository)
):
    """새로운 사용자 생성"""
    # LoginId 중복 체크
    existing_user = repo.get_user_by_login_id(user_data.LoginId)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LoginId already exists"
        )
    
    new_user = repo.create_user(user_data)
    return new_user

# [R] Read All - GET /v1/users
@router.get("/", response_model=List[User])
def read_users(repo: UserRepository = Depends(get_user_repository)):
    """모든 사용자 목록 조회"""
    return repo.get_all_users()

# [R] Read One - GET /v1/users/{user_id}
@router.get("/{user_id}", response_model=User)
def read_user(user_id: int, repo: UserRepository = Depends(get_user_repository)):
    """특정 사용자 ID로 조회"""
    user = repo.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

# [U] Update - PUT /v1/users/{user_id}
@router.put("/{user_id}", response_model=User)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    repo: UserRepository = Depends(get_user_repository)
):
    """특정 사용자 정보 업데이트"""
    updated_user = repo.update_user(user_id, user_data)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user

# [D] Delete - DELETE /v1/users/{user_id}
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, repo: UserRepository = Depends(get_user_repository)):
    """특정 사용자 삭제"""
    if not repo.delete_user(user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return
