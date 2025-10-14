from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

# Base Schema
class ImageLogBase(BaseModel):
    UserId: int = Field(..., example=1, description="사용자 ID (FK)")
    ImageId: Optional[str] = Field(None, max_length=100, example="img_20250101_001", description="이미지 고유 ID")
    ChunkCount: Optional[int] = Field(None, example=128, description="청크 개수")
    ImageSize: Optional[int] = Field(None, example=5120, description="이미지 크기 (KB)")
    Status: Optional[str] = Field(default="pending", max_length=20, example="pending", description="처리 상태")
    FileBasePath: Optional[str] = Field(None, max_length=255, example="/uploads/images", description="파일 경로")

# Create Schema
class ImageLogCreate(ImageLogBase):
    pass

# Update Schema
class ImageLogUpdate(BaseModel):
    ImageId: Optional[str] = Field(None, max_length=100)
    ChunkCount: Optional[int] = None
    ImageSize: Optional[int] = None
    EndAt: Optional[datetime] = None
    Status: Optional[str] = Field(None, max_length=20)
    FileBasePath: Optional[str] = Field(None, max_length=255)
    TotalTime: Optional[int] = None

# Response Schema
class ImageLog(ImageLogBase):
    ImageLogId: int = Field(..., example=1, description="로그 ID")
    CreateAt: Optional[datetime] = Field(None, description="생성 시각")
    EndAt: Optional[datetime] = Field(None, description="완료 시각")
    TotalTime: Optional[int] = Field(None, example=450, description="총 처리 시간 (밀리초)")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )
