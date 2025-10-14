# app/main.py (또는 프로젝트의 entry point)

from fastapi import FastAPI
from app.api.v1.endpoints.Auth import router as auth_router_v1
from app.database.Database import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from app.core import Models
from app.api.v1.endpoints.User import router as user_router_v1
Base.metadata.create_all(bind=engine)

# 1. FastAPI 애플리케이션 생성
app = FastAPI(
    title="User CRUD + auth",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth_router_v1, prefix="/v1")
app.include_router(user_router_v1, prefix="/v1")

# 기본 경로 테스트
@app.get("/")
def root():
    return {"message": "OK"}