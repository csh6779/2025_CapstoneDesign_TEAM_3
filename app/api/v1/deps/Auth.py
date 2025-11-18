# app/api/v1/deps/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.Jwt import decode_token
from app.database.database import get_db
from app.repositories.user import UserRepository

# Auth.py에서 지정한 tokenUrl과 동일하게!
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token")
repo = UserRepository()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 유효하지 않거나 만료되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="토큰에 사용자 정보가 없습니다.")

    user = repo.get_user_by_id(db, int(user_id))  # repo에 이미 있음(파일 일부 생략돼 있지만 구현되어 있음)
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    return user

def require_roles(*roles: str):
    def _checker(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
    ):
        from jose import JWTError
        try:
            payload = decode_token(token)
        except JWTError:
            raise HTTPException(status_code=401, detail="토큰이 유효하지 않습니다.")

        role = payload.get("role")
        if not role or role.lower() not in [r.lower() for r in roles]:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
        user_id = payload.get("sub")
        user = repo.get_user_by_id(db, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
        return user
    return _checker
