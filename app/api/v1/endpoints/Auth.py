from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database.Database import get_db
from app.core.Jwt import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.repositories import User as user_repo
from app.schemas.Users import Token
from datetime import timedelta # <--- 이 임포트를 추가해야 timedelta를 사용할 수 있습니다.

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={401: {"description": "Authentication Failed"}},
)

def AuthenticateUser(db: Session, LoginId: str, Password: str):
    """
    사용자 ID와 비밀번호를 검증합니다.
    """
    user = user_repo.get_user_by_login_id(db, loginId=LoginId)
    if not user:
        return None
    
    # HashedPassword와 입력된 비밀번호 비교
    if not verify_password(Password, user.HashedPassword):
        return None
        
    return user

@router.post("/token", response_model=Token)
async def LoginAccessToken(
    FormData: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    로그인을 처리하고 JWT Access Token을 발급합니다.
    """
    # 1. 사용자 인증
    user = AuthenticateUser(
        db, 
        loginId=FormData.usernameserName, # OAuth2PasswordRequestForm은 username 필드 사용
        password=FormData.password
    )
    
    if not user:
        # 인증 실패 시 401 Unauthorized 반환
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. 토큰 생성 (Payload에 User ID를 넣습니다)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "Role": user.Role}, # 이전 요청에 따라 'role'을 'Role'로 수정했습니다.
        expires_delta=access_token_expires
    )
    
    # 3. 토큰 응답
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "expires_in_minutes": ACCESS_TOKEN_EXPIRE_MINUTES
    }