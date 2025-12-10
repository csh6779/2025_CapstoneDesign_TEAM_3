"""ImageLog 데이터베이스 모델"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database.database import Base
from datetime import datetime

class ImageLog(Base):
    """이미지 처리 로그 테이블"""
    __tablename__ = "ImageLog"

    ImageLogId = Column(Integer, primary_key=True, autoincrement=True, index=True)
    UserId = Column(Integer, ForeignKey("Users.id", ondelete="CASCADE"), nullable=False, index=True)
    ImageId = Column(String(100), nullable=True)
    ChunkCount = Column(Integer, nullable=True)
    ImageSize = Column(Integer, nullable=True)  # KB 단위
    CreateAt = Column(DateTime, nullable=False, default=datetime.utcnow)
    EndAt = Column(DateTime, nullable=True)
    Status = Column(String(20), nullable=False, default="pending")  # pending, processing, completed, failed
    FileBasePath = Column(String(255), nullable=True)
    TotalTime = Column(Integer, nullable=True)  # 밀리초 단위

    # Users와의 관계 (N:1)
    user = relationship("User", back_populates="image_logs")

    def __repr__(self):
        return f"<ImageLog(ImageLogId={self.ImageLogId}, UserId={self.UserId}, Status='{self.Status}')>"
