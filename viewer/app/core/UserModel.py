"""User 데이터베이스 모델"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime

class User(Base):
    """사용자 테이블"""
    __tablename__ = "Users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    LoginId = Column(String(50), unique=True, nullable=False, index=True)
    PasswordHash = Column(String(255), nullable=False)
    UserName = Column(String(30), nullable=False)
    Role = Column(String(10), nullable=False, default="user")  # user, admin
    UserImage = Column(String(255), nullable=True)
    CreatedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    UpdatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 관계 설정
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    image_logs = relationship("ImageLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, LoginId='{self.LoginId}', UserName='{self.UserName}', Role='{self.Role}')>"
