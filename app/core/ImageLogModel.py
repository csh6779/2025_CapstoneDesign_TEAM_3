from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.database import Base
from datetime import datetime

class ImageLog(Base):
    __tablename__ = "ImageLog"

    ImageLogId = Column(Integer, primary_key=True, autoincrement=True, index=True)
    UserId = Column(Integer, ForeignKey("Users.id"), nullable=False)
    ImageId = Column(String(100), nullable=True)
    ChunkCount = Column(Integer, nullable=True)
    ImageSize = Column(Integer, nullable=True)
    CreateAt = Column(DateTime, nullable=True, default=datetime.utcnow)
    EndAt = Column(DateTime, nullable=True)
    Status = Column(String(20), nullable=True, default="pending")
    FileBasePath = Column(String(255), nullable=True)
    TotalTime = Column(Integer, nullable=True)

    # Users와의 관계 (N:1)
    user = relationship("User", back_populates="image_logs")

    def __repr__(self):
        return f"<ImageLog(ImageLogId={self.ImageLogId}, UserId={self.UserId}, Status='{self.Status}')>"
