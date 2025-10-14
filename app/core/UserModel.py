from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database.database import Base

class User(Base):
    __tablename__ = "Users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    LoginId = Column(String(50), unique=True, nullable=False, index=True)
    PasswordHash = Column(String(255), nullable=False)
    UserName = Column(String(30), nullable=False)
    Role = Column(String(10), nullable=True, default="user")
    UserImage = Column(String(255), nullable=True)

    # ImageLog와의 관계 (1:N)
    image_logs = relationship(
        "ImageLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, LoginId='{self.LoginId}', UserName='{self.UserName}')>"
