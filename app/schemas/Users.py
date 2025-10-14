# app/schemas/Users.py
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

# 공통: ORM 객체에서 속성 읽기 활성화 + 이름 기준 직렬화 허용
_BASE_CONFIG = ConfigDict(from_attributes=True, populate_by_name=True)

class UserBase(BaseModel):
    LoginId: str = Field(..., example="Admin")
    UserName: str = Field(..., example="홍길동")
    Role: str = Field(..., example="Bronze")
    UserImage: str = Field(..., example="프로필 사진.jpg")
    Count: int = Field(..., example=0)

    model_config = _BASE_CONFIG

class UserCreate(UserBase):
    Password: str = Field(..., min_length=8, max_length=128)
    AdminCode: int = Field(..., example=123)

class UserUpdate(BaseModel):
    UserName: Optional[str] = Field(default=None, min_length=1, max_length=50)
    Role: Optional[str] = Field(default=None, max_length=20)
    UserImage: Optional[str] = Field(default=None, max_length=255)
    Count: Optional[int] = Field(default=None, ge=0)
    Password: Optional[str] = Field(default=None, min_length=8, max_length=128)

    model_config = _BASE_CONFIG

class UserOut(UserBase):
    # ORM의 대문자 'Id'를 읽어서 응답은 소문자 'id'로 직렬화
    id: int = Field(validation_alias="Id")

    model_config = _BASE_CONFIG

class Token(BaseModel):
    AccessToken: str = Field(..., description="JWT 엑세스 토큰")
    TokenType: str = Field("bearer", description="토큰 타입")
    ExpiresInMin: int = Field(..., description="토큰 만료 (분)")

    model_config = _BASE_CONFIG

class TokenData(BaseModel):
    sub: Optional[str] = None
    Role: Optional[str] = None  # 토큰에 넣는 키가 'role'이라면 여기도 'role'로 맞추세요.

    model_config = _BASE_CONFIG
