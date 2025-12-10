"""인증 API - 로그인/회원가입 (JSON 기반)"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from core.Jwt import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from repositories.json_user_repository import JSONUserRepository
from schemas.Users import UserSignup, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["인증"])

user_repo = JSONUserRepository()

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignup):
    """
    회원가입
    - LoginId는 중복 불가
    - 비밀번호는 자동으로 해싱됨
    """
    # 중복 확인
    existing_user = user_repo.get_user_by_login_id(payload.LoginId)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 아이디입니다."
        )
    
    # 사용자 생성
    new_user = user_repo.create_user(payload)
    
    return new_user

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    로그인 (JWT Token 발급)
    - username: LoginId
    - password: Password
    """
    # 사용자 인증
    user = user_repo.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Access Token 생성
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "AccessToken": access_token,
        "TokenType": "bearer",
        "ExpiresInMin": ACCESS_TOKEN_EXPIRE_MINUTES
    }
