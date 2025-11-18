# app/database/database.py (SQLite 버전 - 개발/테스트용)

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SQLite 데이터베이스 파일 경로
DB_PATH = BASE_DIR / "app.db"

# SQLite 연결 URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLAlchemy Engine 생성
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # SQLite only
)

# SessionLocal (세션 클래스) 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base 생성
Base = declarative_base()

# Dependency (의존성 주입) 함수 정의
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

print(f"[Database] SQLite 사용: {DB_PATH}")
