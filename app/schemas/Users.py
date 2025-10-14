from pydantic import BaseModel, Field
from typing import Optional

# Base Schema: 모든 사용자 모델의 기본 필드를 정의
class UserBase(BaseModel):
    LoginId: str = Field(..., min_length=1, max_length=50, example="user123")
    UserName: str = Field(..., min_length=1, max_length=30, example="홍길동")
    Role: Optional[str] = Field(default="user", max_length=10, example="user")
    UserImage: Optional[str] = Field(default=None, max_length=255, example="profile.jpg")

# Create Schema: 사용자 생성 요청 시 클라이언트로부터 받는 데이터
class UserCreate(BaseModel):
    LoginId: str = Field(..., min_length=1, max_length=50, example="user123")
    Password: str = Field(..., min_length=8, example="password123")
    UserName: str = Field(..., min_length=1, max_length=30, example="홍길동")
    Role: Optional[str] = Field(default="user", max_length=10, example="user")
    UserImage: Optional[str] = Field(default=None, max_length=255, example="profile.jpg")

# Update Schema: 사용자 정보 업데이트 요청 시 클라이언트로부터 받는 데이터 (모두 선택적)
class UserUpdate(BaseModel):
    LoginId: Optional[str] = Field(None, max_length=50)
    Password: Optional[str] = Field(None, min_length=8)
    UserName: Optional[str] = Field(None, max_length=30)
    Role: Optional[str] = Field(None, max_length=10)
    UserImage: Optional[str] = Field(None, max_length=255)

# Response Schema: 사용자 정보를 클라이언트에게 응답할 때 사용하는 데이터
class User(BaseModel):
    id: int = Field(..., example=1)
    LoginId: str = Field(..., example="user123")
    UserName: str = Field(..., example="홍길동")
    Role: str = Field(..., example="user")
    UserImage: Optional[str] = Field(None, example="profile.jpg")

    class Config:
        from_attributes = True  # Pydantic v2

# JWT 토큰 관련 스키마
class Token(BaseModel):
    AccessToken: str = Field(..., description="JWT 액세스 토큰")
    TokenType: str = Field("bearer", description="토큰 타입")
    ExpiresInMin: int = Field(..., description="토큰 만료 (분)")

class TokenData(BaseModel):
    sub: Optional[str] = None
    Role: Optional[str] = None
