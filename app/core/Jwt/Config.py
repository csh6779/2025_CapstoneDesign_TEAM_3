# app/core/Jwt/Config.py
import os
from pydantic import BaseModel
from dotenv import load_dotenv

# .env 로드 (프로젝트 루트에 .env 파일 위치)
load_dotenv()

class Settings(BaseModel):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_key_here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

settings = Settings()
