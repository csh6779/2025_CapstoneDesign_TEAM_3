# app/api/v1/endpoints/Auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Annotated

from app.database.Database import get_db
from app.repositories.User import UserRepository
from app.schemas.Users import Token
from app.core.Jwt.Security import create_access_token
from app.core.Jwt.Config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# /v1 프리픽스 기준 token 엔드포인트 경로와 일치하게!
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

repo = UserRepository()

@router.post("/token", response_model=Token)
def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    # OAuth2PasswordRequestForm는 username, password 필드를 준다.
    # 레포는 login_id 인자를 받도록 되어 있으니 매핑해서 호출.
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
    return Token(
        AccessToken=access_token,
        TokenType="bearer",
        ExpiresInMin=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
