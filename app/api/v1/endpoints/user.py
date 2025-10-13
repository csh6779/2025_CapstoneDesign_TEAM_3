# app/api/v1/endpoints/user.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

# 임포트 경로 수정: schemas와 repositories는 app 디렉토리 기준으로 임포트합니다.
from app.schemas.Users import User, UserCreate, UserUpdate
from app.repositories.User import UserRepository 

router = APIRouter(
    prefix="/users", # 경로 접두사 설정
    tags=["users"]   # API 문서에 표시될 태그
)

# Repository 인스턴스를 얻기 위한 의존성 함수
def get_user_repository() -> UserRepository:
    """Repository 인스턴스를 제공하는 의존성 주입 (Dependency Injection) 함수"""
    return UserRepository()

# [C] Create - POST /v1/users
@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate, 
    repo: UserRepository = Depends(get_user_repository)
):
    """새로운 사용자 생성"""
    # 1. 요청 데이터를 Pydantic 스키마(UserCreate)로 검증/수신
    # 2. Repository 계층에 데이터 생성 요청
    new_user = repo.create_user(user_data)
    # 3. Pydantic 스키마(User)로 변환된 결과 반환 (status_code 201)
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
        # 사용자가 없으면 404 Not Found 에러 발생
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
        # 삭제할 사용자가 없어도 404를 반환할 수 있지만, 
        # 여기서는 삭제 성공 여부만 확인하고 성공 시 204 No Content 반환
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # 성공적으로 삭제되면 204 No Content 응답 (FastAPI가 자동으로 해줌)
    return