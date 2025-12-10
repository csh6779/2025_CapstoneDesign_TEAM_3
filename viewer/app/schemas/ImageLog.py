"""ImageLog Pydantic 스키마"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 이미지 로그 생성 요청
class ImageLogCreate(BaseModel):
    ImageId: Optional[str] = Field(None, max_length=100)
    ChunkCount: Optional[int] = None
    ImageSize: Optional[int] = None  # KB 단위
    Status: str = Field(default="pending", description="pending, processing, completed, failed")
    FileBasePath: Optional[str] = Field(None, max_length=255)

# 이미지 로그 업데이트 요청
class ImageLogUpdate(BaseModel):
    Status: Optional[str] = None
    ChunkCount: Optional[int] = None
    EndAt: Optional[datetime] = None
    TotalTime: Optional[int] = None  # 밀리초

# 이미지 로그 완료 요청
class ImageLogComplete(BaseModel):
    TotalTime: int = Field(..., description="총 처리 시간 (밀리초)")

# 이미지 로그 응답
class ImageLogResponse(BaseModel):
    ImageLogId: int
    UserId: int
    ImageId: Optional[str]
    ChunkCount: Optional[int]
    ImageSize: Optional[int]
    CreateAt: datetime
    EndAt: Optional[datetime]
    Status: str
    FileBasePath: Optional[str]
    TotalTime: Optional[int]

    class Config:
        from_attributes = True
