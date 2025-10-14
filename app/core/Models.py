# app/core/models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.Database import Base

class User(Base):
    __tablename__ = "users"

    Id = Column(Integer, primary_key=True, index=True)
    LoginId = Column(String(50), unique=True, index=True)
    HashedPassword = Column(String(255))
    UserName = Column(String(50))
    Role = Column(String(20), default="bronze")
    UserImage = Column(String(255), nullable=True)
    Count = Column(Integer, default=0)

    # 1:1 로그라면 uselist=False
    Log = relationship("Log", back_populates="User", uselist=False)
    # 1:N 로그로 바꾸고 싶으면: Log = relationship("Log", back_populates="User", uselist=True, cascade="all, delete-orphan")

class Log(Base):
    __tablename__ = "logs"

    Id = Column(Integer, primary_key=True)
    UserId = Column(Integer, ForeignKey("users.Id"), nullable=False, unique=True)  # 1:1이면 unique=True
    Action = Column(String(50))
    CreatedAt = Column(DateTime, server_default=func.now())

    User = relationship("User", back_populates="Log")

    # 1:N로 바꿀 경우:
    # UserId = Column(Integer, ForeignKey("users.Id"), nullable=False)  # unique 제거
    # 그리고 User.Log에서 uselist=True로
