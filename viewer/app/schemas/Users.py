"""User Pydantic 스키마"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 회원가입 요청
class UserSignup(BaseModel):
    LoginId: str = Field(..., min_length=4, max_length=50, description="로그인 ID")
    Password: str = Field(..., min_length=6, description="비밀번호")
    UserName: str = Field(..., min_length=2, max_length=30, description="사용자 이름")
    Role: Optional[str] = Field(default="user", description="권한 (user/admin)")
    UserImage: Optional[str] = Field(default=None, description="프로필 이미지 경로")

# 로그인 요청
class UserLogin(BaseModel):
    LoginId: str
    Password: str

# 사용자 정보 업데이트
class UserUpdate(BaseModel):
    UserName: Optional[str] = Field(None, min_length=2, max_length=30)
    Password: Optional[str] = Field(None, min_length=6)
    UserImage: Optional[str] = None

# 사용자 응답
class UserResponse(BaseModel):
    id: int
    LoginId: str
    UserName: str
    Role: str
    UserImage: Optional[str]
    CreatedAt: datetime
    UpdatedAt: datetime

    class Config:
        from_attributes = True

# 토큰 응답
class Token(BaseModel):
    AccessToken: str
    TokenType: str = "bearer"
    ExpiresInMin: int

# 토큰 데이터
class TokenData(BaseModel):
    user_id: Optional[int] = None
