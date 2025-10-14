# app/database/Database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL",
 "mysql+pymysql://root:1234@127.0.0.1:3306/capstone?charset=utf8mb4")

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    echo=True,  # 개발 중 SQL 확인 원하면 True
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine,future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
