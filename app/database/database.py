# app/database/database.py (MySQL용)

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. MySQL DB 연결 URL 설정
# 형식: mysql+pymysql://<user>:<password>@<host>:<port>/<dbname>
# 실제 환경에 맞게 [user], [password], [host], [dbname] 부분을 수정해야 합니다.
# 예시:
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/capstone"

# 2. SQLAlchemy Engine 생성
# PyMySQL을 사용하므로 connect_args는 필요 없습니다.
# pool_recycle 옵션은 MySQL 서버가 비활성 연결을 끊는 경우를 처리하는 데 도움이 됩니다.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_recycle=3600 # 1시간마다 연결 재활용 (선택 사항)
)

# 3. SessionLocal (세션 클래스) 생성 (SQLite와 동일)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Declarative Base 생성 (SQLite와 동일)
Base = declarative_base()

# 5. Dependency (의존성 주입) 함수 정의 (SQLite와 동일)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()