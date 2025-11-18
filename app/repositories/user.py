# app/repositories/user.py

from typing import List, Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.core.UserModel import User as UserModel
from app.schemas.Users import UserCreate, UserUpdate

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository:
    """User 데이터를 관리하는 Repository 클래스"""

    def __init__(self):
        pass

    def _hash_password(self, password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)

    def create_user(self, db: Session, payload: UserCreate) -> UserModel:
        """새로운 사용자 생성"""
        # 비밀번호 해싱
        hashed_password = self._hash_password(payload.Password)
        
        # UserModel 인스턴스 생성
        new_user = UserModel(
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

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[UserModel]:
        """ID로 사용자 조회"""
        return db.query(UserModel).filter(UserModel.id == user_id).first()

    def get_user_by_login_id(self, db: Session, login_id: str) -> Optional[UserModel]:
        """LoginId로 사용자 조회 (인증용)"""
        return db.query(UserModel).filter(UserModel.LoginId == login_id).first()

    def get_user(self, db: Session) -> List[UserModel]:
        """모든 사용자 조회"""
        return db.query(UserModel).all()

    def update_user(self, db: Session, user_id: int, **kwargs) -> Optional[UserModel]:
        """사용자 정보 업데이트"""
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            return None
        
        # 업데이트할 필드만 적용
        for key, value in kwargs.items():
            if value is not None:
                if key == "Password":
                    setattr(user, "PasswordHash", self._hash_password(value))
                elif hasattr(user, key):
                    setattr(user, key, value)
        
        db.commit()
        db.refresh(user)
        
        return user

    def delete_user(self, db: Session, user_id: int) -> bool:
        """사용자 삭제"""
        user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def authenticate_user(self, db: Session, login_id: str, password: str) -> Optional[UserModel]:
        """사용자 인증"""
        user = self.get_user_by_login_id(db, login_id)
        if not user:
            return None
        if not self.verify_password(password, user.PasswordHash):
            return None
        return user
