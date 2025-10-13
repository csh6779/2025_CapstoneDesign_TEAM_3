from pydantic import BaseModel, Field
from typing import Optional

# Base Schema: 모든 사용자 모델의 기본 필드를 정의 (사용자 생성/업데이트 시 사용)
class UserBase(BaseModel):
    LoginId: str = Field(..., example="Admin")
    UserName: str = Field(..., example="홍길동")
    Role : str = Field(...,example="Bronze")
    UserImage : str = Field(..., example="프로필 사진.jpg")
    Count: int = Field(..., example=0)

# Create Schema: 사용자 생성 요청 시 클라이언트로부터 받는 데이터
class UserCreate(UserBase):
    Password: str = Field(..., min_length=8)
    AdminCode : int = Field(...,example=123)
    
# Update Schema: 사용자 정보 업데이트 요청 시 클라이언트로부터 받는 데이터 (모두 선택적)
class UserUpdate(UserBase):
    LoginId: Optional[str] = None
    UserName: Optional[str] = None
    Password: Optional[str] =Field(None, min_length=8)
    Role : Optional[str] = Field(None, example="Sliver") 
    UserImage : Optional[str] = Field(None, example="수정된 프로필 사진.jpg")
    Count : Optional[int] = Field(None, example=1)
        
# Response Schema: 사용자 정보를 클라이언트에게 응답할 때 사용하는 데이터
# 민감한 정보(예: 비밀번호)는 제외하고, ID 같은 추가 필드를 포함합니다.
class User(UserBase):
    id: int = Field(..., example=1)
    
    # ORM 모드를 활성화하여 딕셔너리나 ORM 객체에서 필드를 읽을 수 있게 합니다.
    class Config:
        from_attributes = True # Pydantic v2
        # orm_mode = True # Pydantic v1

class Token(BaseModel):
    AccessToken:str = Field(..., description="JWT 엑세스 토큰")
    TokenType : str = Field("bearer", description="토큰 타입")
    ExpiresInMin : int = Field(..., description="토큰 만료 (분)")

class TokenData(BaseModel):
    sub: Optional[str] = None
    Role: Optional[str] = None