# app/api/v1/endpoints/Auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.database.database import get_db
from app.repositories.user import UserRepository
from app.schemas.Users import Token, User as UserOut
from app.core.Jwt import create_access_token, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.api.v1.deps.Auth import get_current_user
from app.utils.ncsa_logger import ncsa_logger


router = APIRouter(prefix="/auth", tags=["auth"])

# /v1 프리픽스 기준 token 엔드포인트 경로와 일치하게!
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")

repo = UserRepository()

@router.get("/me", response_model=UserOut)
async def read_me(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    # 내 정보 확인 로깅
    await ncsa_logger.log_request(
        request=request,
        response=response,
        auth_user=current_user.UserName,
        activity_type="CHECK_AUTH",
        details={"user_id": current_user.id}
    )
    
    return current_user

@router.post("/token", response_model=Token)
async def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = repo.authenticate_user(db, login_id=form_data.username, password=form_data.password)
    
    if not user:
        # 로그인 실패 로깅
        await ncsa_logger.log_request(
            request=request,
            response=response,
            activity_type="LOGIN_FAILED",
            details={"login_id": form_data.username, "reason": "invalid_credentials"}
        )
        
        # 실패 활동 로깅 (사용자명이 아닌 시도한 로그인 ID로)
        ncsa_logger.log_activity(
            username="anonymous",
            activity="LOGIN_ATTEMPT_FAILED",
            status="FAILED",
            details={
                "attempted_login_id": form_data.username,
                "remote_host": request.client.host if request.client else "unknown"
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=str(user.id),  # 모델 컬럼 대소문자 주의(Id -> id로 수정)
        role=getattr(user, "Role", None),
        expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    
    token = Token(
        AccessToken=access_token,
        TokenType="bearer",
        ExpiresInMin=ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    
    # 로그인 성공 로깅
    await ncsa_logger.log_request(
        request=request,
        response=response,
        auth_user=user.UserName,
        activity_type="LOGIN",
        details={
            "user_id": user.id,
            "login_id": user.LoginId,
            "role": user.Role
        }
    )
    
    # 사용자별 활동 로깅
    ncsa_logger.log_activity(
        username=user.UserName,
        activity="LOGIN_SUCCESS",
        status="SUCCESS",
        details={
            "remote_host": request.client.host if request.client else "unknown",
            "token_expires_min": ACCESS_TOKEN_EXPIRE_MINUTES
        }
    )
    
    return token.model_dump(by_alias=True)

# 토큰 리프레시
@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user)
):
    new_token = create_access_token(
        subject=str(current_user.id),
        role=getattr(current_user, "Role", None),
        expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    
    token = Token(
        AccessToken=new_token,
        TokenType="bearer",
        ExpiresInMin=ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    
    # 토큰 리프레시 로깅
    await ncsa_logger.log_request(
        request=request,
        response=response,
        auth_user=current_user.UserName,
        activity_type="TOKEN_REFRESH",
        details={
            "user_id": current_user.id,
            "token_expires_min": ACCESS_TOKEN_EXPIRE_MINUTES
        }
    )
    
    ncsa_logger.log_activity(
        username=current_user.UserName,
        activity="TOKEN_REFRESHED",
        status="SUCCESS",
        details={"token_expires_min": ACCESS_TOKEN_EXPIRE_MINUTES}
    )
    
    return token.model_dump(by_alias=True)