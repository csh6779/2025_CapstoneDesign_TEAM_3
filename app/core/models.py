# app/core/models.py (MySQL용 - 길이 명시)

from sqlalchemy import Column, Integer, String
from app.database.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    LoginID = Column(String(50), unique=True, index=True) 
    Password = Column(String(100)) 
    UserName = Column(String(50))
    Role = Column(String(20), default="user")

    def __repr__(self):
        return f"<User(id={self.id}, loginId='{self.LoginID}')>"