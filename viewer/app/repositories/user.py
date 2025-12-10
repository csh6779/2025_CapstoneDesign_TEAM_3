"""User Repository - 사용자 CRUD"""
from sqlalchemy.orm import Session
from typing import List, Optional
from passlib.context import CryptContext

from core.UserModel import User
from schemas.Users import UserSignup, UserUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository:
    """사용자 데이터 접근 레이어"""

    def _hash_password(self, password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)

    def create_user(self, db: Session, payload: UserSignup) -> User:
        """새로운 사용자 생성"""
        # 비밀번호 해싱
        hashed_password = self._hash_password(payload.Password)
        
        # User 인스턴스 생성
        new_user = User(
            LoginId=payload.LoginId,
            PasswordHash=hashed_password,
            UserName=payload.UserName,
            Role=payload.Role or "user",
            UserImage=payload.UserImage
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        return db.query(User).filter(User.id == user_id).first()

    def get_user_by_login_id(self, db: Session, login_id: str) -> Optional[User]:
        """LoginId로 사용자 조회 (인증용)"""
        return db.query(User).filter(User.LoginId == login_id).first()

    def get_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """모든 사용자 조회 (페이지네이션)"""
        return db.query(User).offset(skip).limit(limit).all()

    def update_user(self, db: Session, user_id: int, payload: UserUpdate) -> Optional[User]:
        """사용자 정보 업데이트"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # 업데이트할 필드만 적용
        if payload.UserName is not None:
            user.UserName = payload.UserName
        if payload.Password is not None:
            user.PasswordHash = self._hash_password(payload.Password)
        if payload.UserImage is not None:
            user.UserImage = payload.UserImage
        
        db.commit()
        db.refresh(user)
        
        return user

    def delete_user(self, db: Session, user_id: int) -> bool:
        """사용자 삭제"""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def authenticate_user(self, db: Session, login_id: str, password: str) -> Optional[User]:
        """사용자 인증"""
        user = self.get_user_by_login_id(db, login_id)
        if not user:
            return None
        if not self.verify_password(password, user.PasswordHash):
            return None
        return user
