from datetime import datetime, timedelta, timezone
from typing import Any
from jose import jwt
from passlib.context import CryptContext

# -----------------
# Configuration
# -----------------

# 실제 환경에서는 환경 변수에서 가져와야 합니다.
SECRET_KEY = "my_actual_secure_jwt_key_42"  # <-- 반드시 변경하세요!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -----------------
# Password Hashing Functions
# -----------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """평문 비밀번호와 해시된 비밀번호를 비교합니다."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """비밀번호를 해싱합니다."""
    return pwd_context.hash(password)

# -----------------
# JWT Functions
# -----------------

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    JWT Access Token을 생성합니다.
    Payload에는 주로 sub (Subject, 사용자 ID)와 exp (Expiration, 만료 시간)가 포함됩니다.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # 기본 만료 시간 적용
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # exp 필드 추가
    to_encode.update({"exp": expire})
    
    # JWT 인코딩
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# -----------------
# Dependency Function (Authorization)
# -----------------
# 토큰 인증을 위한 Dependency는 별도의 엔드포인트 파일에서 정의합니다.