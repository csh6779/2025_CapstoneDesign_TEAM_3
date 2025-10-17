# app/core/security.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict, TypedDict

from jose import jwt, JWTError, ExpiredSignatureError
from passlib.context import CryptContext

from app.core.Jwt.Config import settings  

pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


def _normalize_str(s: Any) -> str:
    """bytes로 들어오거나 공백이 끼어도 안전하게 정규화."""
    if isinstance(s, bytes):
        s = s.decode("utf-8", errors="ignore")
    return str(s).strip()


def verify_password(plain: str | bytes, hashed: str) -> bool:
    """
    평문 비밀번호와 저장된 해시를 검증한다.
    - bytes로 들어오는 경우를 대비해 utf-8 디코딩
    - 공백 제거 후 검증
    """
    plain_norm = _normalize_str(plain)
    return pwd_context.verify(plain_norm, hashed)


def hash_password(plain: str | bytes) -> str:
    """
    평문 비밀번호를 해시한다.
    - 신규 해시는 bcrypt_sha256 스킴으로 생성됨
    """
    plain_norm = _normalize_str(plain)
    return pwd_context.hash(plain_norm)

class TokenPayload(TypedDict, total=False):
    sub: str              # 사용자 식별자 (문자열 권장)
    role: str             # 선택적 역할
    iat: int              # issued at (epoch seconds)
    exp: int              # expiration (epoch seconds)
    # 여기에 필요한 커스텀 클레임을 자유롭게 추가 가능


def create_access_token(
    subject: str,
    role: Optional[str] = None,
    expires_minutes: Optional[int] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    액세스 토큰(JWT) 생성.
    - sub: 사용자 식별자 (문자열 권장)
    - role: 선택적 역할 클레임
    - exp/iat: epoch seconds
    """
    now = datetime.now(timezone.utc)
    exp_minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES

    to_encode: TokenPayload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
    }
    if role:
        to_encode["role"] = role
    if extra_claims:
        # 충돌 방지: sub/iat/exp/role 덮어쓰지 않도록 주의(필요 시 정책 정의)
        for k, v in extra_claims.items():
            if k not in ("sub", "iat", "exp"):
                to_encode[k] = v  # type: ignore[assignment]

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """
    토큰 디코드 및 서명/만료 검증.
    - 기본적으로 aud 검증은 사용하지 않으므로 verify_aud=False 옵션 적용.
    - 검증 실패/만료 시 jose 예외(JWTError, ExpiredSignatureError) 발생 → 상위 레이어에서 처리.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"verify_aud": False},
    )  # type: ignore[return-value]


def get_token_subject(token: str) -> str:
    """
    토큰에서 sub(사용자 식별자)를 추출.
    - sub 누락 시 JWTError를 발생시켜 상위에서 401 처리하기 쉽도록 함.
    """
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise JWTError("Token missing 'sub' claim")
    return sub


def get_token_role(token: str) -> Optional[str]:
    """토큰에서 role(역할) 클레임을 선택적으로 추출."""
    payload = decode_token(token)
    role = payload.get("role")
    return str(role) if role is not None else None


def get_token_expiry_remaining(token: str) -> Optional[int]:
    """
    토큰 만료까지 남은 시간(초)을 반환. exp가 없거나 이미 만료면 None.
    상위에서 슬라이딩/리프레시 조건 판단에 활용 가능.
    """
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        return None

    exp = payload.get("exp")
    if not isinstance(exp, int):
        return None
    now = int(datetime.now(timezone.utc).timestamp())
    remain = exp - now
    return remain if remain > 0 else None
