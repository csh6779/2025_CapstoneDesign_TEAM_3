"""Bookmark Pydantic 스키마"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 북마크 생성 요청
class BookmarkCreate(BaseModel):
    VolumeName: str = Field(..., description="볼륨 이름")
    VolumeUrl: str = Field(..., description="Neuroglancer URL")
    Title: Optional[str] = Field(None, max_length=255, description="사용자 지정 제목")
    Description: Optional[str] = Field(None, description="설명")

# 북마크 업데이트 요청
class BookmarkUpdate(BaseModel):
    Title: Optional[str] = Field(None, max_length=255)
    Description: Optional[str] = None

# 북마크 응답
class BookmarkResponse(BaseModel):
    BookmarkId: int
    UserId: int
    VolumeName: str
    VolumeUrl: str
    Title: Optional[str]
    Description: Optional[str]
    CreatedAt: datetime
    UpdatedAt: datetime

    class Config:
        from_attributes = True
