# app/repositories/user.py

from typing import List, Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.core.UserModel import User as UserModel
from app.schemas.Users import UserCreate, UserUpdate, User

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRepository:
    """User 데이터를 관리하는 Repository 클래스"""

    def __init__(self, db: Session):
        self.db = db

    def _hash_password(self, password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)

    def create_user(self, user_data: UserCreate) -> User:
        """새로운 사용자 생성"""
        # 비밀번호 해싱
        hashed_password = self._hash_password(user_data.Password)
        
        # UserModel 인스턴스 생성
        new_user = UserModel(
            LoginId=user_data.LoginId,
            PasswordHash=hashed_password,
            UserName=user_data.UserName,
            Role=user_data.Role or "user",
            UserImage=user_data.UserImage
        )
        
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        
        return User.model_validate(new_user)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            return User.model_validate(user)
        return None

    def get_user_by_login_id(self, login_id: str) -> Optional[UserModel]:
        """LoginId로 사용자 조회 (인증용)"""
        return self.db.query(UserModel).filter(UserModel.LoginId == login_id).first()

    def get_all_users(self) -> List[User]:
        """모든 사용자 조회"""
        users = self.db.query(UserModel).all()
        return [User.model_validate(user) for user in users]

    def update_user(self, user_id: int, update_data: UserUpdate) -> Optional[User]:
        """사용자 정보 업데이트"""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            return None
        
        # 업데이트할 필드만 적용
        update_fields = update_data.model_dump(exclude_unset=True)
        
        # 비밀번호가 있으면 해싱
        if "Password" in update_fields:
            update_fields["PasswordHash"] = self._hash_password(update_fields.pop("Password"))
        
        for field, value in update_fields.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        
        return User.model_validate(user)

    def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        user = self.db.query(UserModel).filter(UserModel.id == user_id).first()
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)
