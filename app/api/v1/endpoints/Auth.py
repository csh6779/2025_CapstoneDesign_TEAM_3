# app/api/v1/endpoints/Auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.database.Database import get_db
from app.repositories.User import UserRepository
from app.schemas.Users import Token, UserOut
from app.core.Jwt.Security import create_access_token
from app.core.Jwt.Config import settings
from app.api.v1.deps.Auth import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])

# /v1 프리픽스 기준 token 엔드포인트 경로와 일치하게!
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

repo = UserRepository()

@router.get("/me", response_model=UserOut)
def read_me(current_user=Depends(get_current_user)):
    return current_user

@router.post("/token", response_model=Token)
def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = repo.authenticate_user(db, login_id=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.Id),  # 모델 컬럼 대소문자 주의(Id)
        role=getattr(user, "Role", None),
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    token = Token(
    AccessToken=access_token,
    TokenType="bearer",
    ExpiresInMin=settings.ACCESS_TOKEN_EXPIRE_MINUTES,)
    return token.model_dump(by_alias=True)

# 토큰 리프레시
@router.post("/refresh", response_model=Token)
def refresh_token(current_user=Depends(get_current_user)):
    from app.core.Jwt.Security import create_access_token
    from app.core.Jwt.Config import settings

    new_token = create_access_token(
        subject=str(current_user.Id),
        role=getattr(current_user  , "Role", None),
        expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    token = Token(
    AccessToken=new_token,
    TokenType="bearer",
    ExpiresInMin=settings.ACCESS_TOKEN_EXPIRE_MINUTES,)
    return token.model_dump(by_alias=True)
