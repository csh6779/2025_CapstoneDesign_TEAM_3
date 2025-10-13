
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database.Database import Base

class User(Base):
    __tablename__ = "users"

    Id = Column(Integer, primary_key=True, index=True)
    LoginId = Column(String(50), unique=True, index=True) 
    HashedPassword= Column(String(100)) 
    UserName = Column(String(50))
    Role = Column(String(20), default="bronze")
    UserImage = Column(String(255), nullable=True) 
    Count = Column(Integer, default=0)


    Log = relationship(
        "Log",               # 문자열 참조: 순환 import 방지
        back_populates="User",
        uselist=False,       # 1:1
        cascade="all, delete-orphan"
    )
    def __repr__(self):
        return f"<User(id={self.Id}, loginId='{self.LoginId}')>"