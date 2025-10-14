# app/api/v1/endpoints/User.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.Database import get_db
from app.repositories.User import UserRepository
from app.schemas.Users import UserCreate, UserUpdate, UserOut

router = APIRouter(prefix="/users", tags=["users"])
repo = UserRepository()

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        user = repo.create_user(db, payload=payload)
        return user
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 아이디 입니다."
        )

@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return repo.list_users(db, skip=skip, limit=limit)

@router.get("/{Id}", response_model=UserOut)
def get_user(Id: int, db: Session = Depends(get_db)):   # 경로변수 이름과 파라미터 이름 일치!
    user = repo.get_user_by_id(db, Id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="없는 사용자 입니다."
        )
    return user

@router.patch("/{Id}", response_model=UserOut)
def update_user(
    Id: int,                                  # ← 경로 변수명과 일치
    payload: UserUpdate,
    db: Session = Depends(get_db),
):
    user = repo.update_user(
        db, Id,
        UserName=payload.UserName,
        Role=payload.Role,
        UserImage=payload.UserImage,
        Count=payload.Count,
        Password=payload.Password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 유저를 찾지 못했습니다."
        )
    return user

@router.delete("/{Id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(Id: int, db: Session = Depends(get_db)):
    ok = repo.delete_user(db, Id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유저를 찾지 못했습니다."
        )
    # 204는 바디 없이 반환
    return
