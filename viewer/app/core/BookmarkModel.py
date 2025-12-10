"""Bookmark 데이터베이스 모델"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime

class Bookmark(Base):
    """북마크 테이블"""
    __tablename__ = "Bookmarks"

    BookmarkId = Column(Integer, primary_key=True, autoincrement=True, index=True)
    UserId = Column(Integer, ForeignKey("Users.id", ondelete="CASCADE"), nullable=False, index=True)
    VolumeName = Column(String(255), nullable=False)
    VolumeUrl = Column(Text, nullable=False)  # Neuroglancer URL
    Title = Column(String(255), nullable=True)  # 사용자 지정 제목
    Description = Column(Text, nullable=True)  # 설명
    CreatedAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    UpdatedAt = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Users와의 관계 (N:1)
    user = relationship("User", back_populates="bookmarks")

    def __repr__(self):
        return f"<Bookmark(BookmarkId={self.BookmarkId}, UserId={self.UserId}, Title='{self.Title}')>"
