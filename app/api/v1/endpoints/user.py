# app/api/v1/endpoints/User.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database.Database import get_db
from app.repositories.User import UserRepository
from app.schemas.Users import UserCreate, UserUpdate, UserOut
from app.api.v1.deps.Auth import get_current_user, require_roles


router = APIRouter(prefix="/users", tags=["users"])
repo = UserRepository()

# 아이디 생성
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

# 전체 유저를 보는건 admin만
@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_admin=Depends(require_roles("Admin","admin"))
):
    users = repo.get_user(db)
    return users

#내 정보 조회 -> 내 정보 수정 페이지에 매핑될 예정
@router.get("/me", response_model=UserOut)
def read_me(current_user=Depends(get_current_user)):
    return current_user

# 단건 조회
@router.get("/{Id}", response_model=UserOut)
def read_user(Id: int, db: Session = Depends(get_db),_=Depends(get_current_user) ):  
    user = repo.get_user_by_id(db,Id)
    if not user:
        raise HTTPException(status_code=404, detail="해당 유저를 찾지 못했습니다.")
    return user

# 내 정보 수정 -> 내 정보 수정에 매핑될 예정
@router.patch("/{Id}", response_model=UserOut)
def update_user(
    Id: int,                                
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
