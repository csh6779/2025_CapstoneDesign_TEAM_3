# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.Jwt.Config import settings  # 기존 경로 유지 (프로젝트 구조에 맞게)

# bcrypt_sha256을 우선으로 사용하고, 기존 bcrypt 해시도 검증 가능하도록 설정
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


def verify_password(plain: str, hashed: str) -> bool:
    """
    평문 비밀번호와 저장된 해시를 검증한다.
    - bytes로 들어오는 경우를 대비해 utf-8 디코딩
    - 공백 제거 후 검증
    """
    if isinstance(plain, bytes):
        plain = plain.decode("utf-8", errors="ignore")
    plain = plain.strip()
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    """
    평문 비밀번호를 해시한다.
    - 신규 해시는 bcrypt_sha256 스킴으로 생성됨
    """
    if isinstance(plain, bytes):
        plain = plain.decode("utf-8", errors="ignore")
    plain = plain.strip()
    return pwd_context.hash(plain)


def create_access_token(
    subject: str,
    role: Optional[str] = None,
    expires_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    액세스 토큰(JWT) 생성.
    - sub: 사용자 식별자 (문자열 권장)
    - role: 선택적 역할 클레임
    - exp/iat: epoch seconds
    """
    now = datetime.now(timezone.utc)
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    if role:
        to_encode["role"] = role
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    토큰 디코드 및 서명/만료 검증.
    필요 시: options={"verify_aud": False} 등을 전달하는 버전으로 확장 가능.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
