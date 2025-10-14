# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import os
import sys
from dotenv import load_dotenv

# === 1) 프로젝트 루트 경로 등록 (alembic/.. = 프로젝트 루트) ===
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# === 2) .env 로드 → DATABASE_URL 사용 ===
load_dotenv()

# === 3) Base 메타데이터 로드 (engine는 가져오지 말고, alembic이 생성) ===
from app.database.Database import Base

# === 4) 반드시 모델들을 import 해야 테이블이 메타데이터에 등록됩니다! ===
#     (중요) 프로젝트의 모든 모델 모듈을 여기서 import 하세요.
from app.core.Models import User as _User  # noqa: F401

config = context.config

# === 5) alembic.ini 대신 .env의 DATABASE_URL을 우선 세팅 ===
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# alembic.ini 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# === 6) 자동 생성에 사용할 메타데이터 지정 ===
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # 스키마 변경 비교 정확도 향상
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode'."""
    # === 7) Alembic이 자체 엔진을 생성하게 둡니다(권장) ===
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # 스키마 변경 비교 정확도 향상
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
