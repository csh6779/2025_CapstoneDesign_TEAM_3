# pydantic v2 권장 설정
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class LogBase(BaseModel):
    UserId: str = Field(..., example="Admin_01", description="로그를 요청한 사용자 ID (FK)")
    ImageId: str = Field(..., example="profile_pic_20250101.jpg", description="처리된 이미지 파일의 고유 ID")
    ChunkCount: int = Field(..., example=128, description="이미지가 분리된 청크의 총 개수")
    ImageSize: int = Field(..., example=5120, description="원본 이미지의 크기 (KB)")
    Status: str = Field("IN_PROGRESS", example="IN_PROGRESS", description="현재 처리 상태")
    FileBasePath: str = Field(..., example=r"C:\Users\USER\Desktop")

class LogCreate(LogBase):
    pass

class LogUpdate(BaseModel):
    EndAt: Optional[datetime] = Field(None, description="청크 분리 완료 시각")
    Status: Optional[str] = Field(None, example="SUCCESS", description="최종 처리 상태 (SUCCESS, FAIL)")
    TotalTime: Optional[int] = Field(None, example=450, description="총 처리 시간 (밀리초)")

class Log(LogBase):
    id: int = Field(..., example=1, alias="LogId", description="로그 레코드의 고유 ID")
    CreateAt: datetime = Field(..., description="청크 분리 처리 시작 시각")
    EndAt: Optional[datetime] = Field(None, description="청크 분리 처리 완료 시각")
    TotalTime: Optional[int] = Field(None, example=450, description="총 처리 시간 (밀리초)")

    model_config = ConfigDict(
        from_attributes=True,   # ORM 객체 -> 스키마 직렬화 허용
        populate_by_name=True   # alias(LogId)로 입출력 허용
    )
