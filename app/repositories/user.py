from sqlalchemy.orm import Session
from typing import Optional, List
from sqlalchemy.exc import IntegrityError
from passlib.exc import PasswordSizeError

from app.schemas.Users import UserCreate, UserUpdate
from app.core.Models import User as UserModel
from app.core.Jwt.Security import verify_password, hash_password


class UserRepository:
    # --- CREATE ---
    def create_user(self, db: Session, *, payload: UserCreate) -> UserModel:
        try:
            hashed_password = hash_password(payload.Password)
        except PasswordSizeError as e:
            # passlib에서 72바이트 초과 등 발생 시 상위로 전달
            raise ValueError(f"비밀번호가 너무 깁니다. ({e})")

        user = UserModel(
            LoginId=payload.LoginId,
            HashedPassword=hashed_password,
            UserName=payload.UserName,
            Role=payload.Role,
            UserImage=payload.UserImage,
            Count=payload.Count,
        )

        db.add(user)
        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            raise  # 라우터에서 409 처리

    # --- READ ---
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.Id == user_id).first()

    # (과거 호환) get_user -> get_user_by_id 위임
    def get_user(self, db: Session, user_id: int) -> Optional[UserModel]:
        return self.get_user_by_id(db, user_id)

    def get_user_by_login_id(self, db: Session, login_id: str) -> Optional[UserModel]:
        return db.query(UserModel).filter(UserModel.LoginId == login_id).first()

    def list_users(self, db: Session, skip: int = 0, limit: int = 50) -> List[UserModel]:
        return (
            db.query(UserModel)
            .order_by(UserModel.Id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    # --- UPDATE ---
    # 엔드포인트에서 전달하는 키워드 인자 시그니처와 일치시킴
    def update_user(
        self,
        db: Session,
        user_id: int,
        *,
        UserName: Optional[str] = None,
        Role: Optional[str] = None,
        UserImage: Optional[str] = None,
        Count: Optional[int] = None,
        Password: Optional[str] = None,
    ) -> Optional[UserModel]:
        user = self.get_user_by_id(db, user_id)
        if not user:
            return None

        if UserName is not None:
            user.UserName = UserName
        if Role is not None:
            user.Role = Role
        if UserImage is not None:
            user.UserImage = UserImage
        if Count is not None:
            user.Count = Count
        if Password is not None:
            try:
                user.HashedPassword = hash_password(Password)
            except PasswordSizeError as e:
                raise ValueError(f"새 비밀번호가 너무 깁니다. ({e})")

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # --- DELETE ---
    def delete_user(self, db: Session, user_id: int) -> bool:
        user = self.get_user_by_id(db, user_id)
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True

    # --- AUTH ---
    def authenticate_user(self, db: Session, *, login_id: str, password: str) -> Optional[UserModel]:
        user = self.get_user_by_login_id(db, login_id)
        if not user:
            return None
        if not verify_password(password, user.HashedPassword):
            return None
        return user
