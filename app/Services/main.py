# app/main.py (또는 프로젝트의 entry point)

from fastapi import FastAPI
from app.api.v1.endpoints import user as user_router_v1
from app.database.Database import engine, Base
from app.core import models

Base.metadata.create_all(bind=engine)

# 1. FastAPI 애플리케이션 생성
app = FastAPI(
    title="User CRUD Example",
    version="1.0.0",
)

# 2. v1 라우터 연결
# include_router의 prefix에 /v1을 추가하여 전체 경로를 /v1/users로 만듭니다.
app.include_router(user_router_v1.router, prefix="/v1")

# 기본 경로 테스트
@app.get("/")
def read_root():
    return {"message": "Welcome to the User CRUD API"}