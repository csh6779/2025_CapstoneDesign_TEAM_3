from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database.database import get_db
from app.core.Jwt import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.repositories import UserRepository
from app.schemas.Users import Token

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={401: {"description": "Authentication Failed"}},
)

def authenticate_user(db: Session, login_id: str, password: str):
    """
    사용자 ID와 비밀번호를 검증합니다.
    """
    user_repo = UserRepository(db)
    
    # LoginId로 사용자 조회
    user = user_repo.get_user_by_login_id(login_id)
    if not user:
        return None
    
    # PasswordHash와 입력된 비밀번호 비교
    if not user_repo.verify_password(password, user.PasswordHash):
        return None
        
    return user

@router.post("/token", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    로그인을 처리하고 JWT Access Token을 발급합니다.
    
    - OAuth2PasswordRequestForm은 username과 password 필드를 사용합니다
    - username 필드에 LoginId를 입력해야 합니다
    """
    # 1. 사용자 인증
    user = authenticate_user(
        db, 
        login_id=form_data.username,  # OAuth2PasswordRequestForm은 username 필드 사용
        password=form_data.password
    )
    
    if not user:
        # 인증 실패 시 401 Unauthorized 반환
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. 토큰 생성 (Payload에 User ID와 Role을 넣습니다)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "Role": user.Role},
        expires_delta=access_token_expires
    )
    
    # 3. 토큰 응답
    return {
        "AccessToken": access_token, 
        "TokenType": "bearer",
        "ExpiresInMin": ACCESS_TOKEN_EXPIRE_MINUTES
    }