"""
데이터베이스 자동 초기화 및 마이그레이션
서버 시작 시 자동으로 실행됩니다.
"""

from sqlalchemy import text, inspect
from app.database.database import engine, Base
from app.core.UserModel import User
from app.core.ImageLogModel import ImageLog
import logging

logger = logging.getLogger(__name__)

def check_column_type(table_name: str, column_name: str) -> str:
    """컬럼의 현재 타입 확인"""
    try:
        with engine.connect() as connection:
            sql = text("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = :table_name 
                AND COLUMN_NAME = :column_name
            """)
            result = connection.execute(sql, {"table_name": table_name, "column_name": column_name})
            row = result.fetchone()
            
            if row:
                return row[0].lower()
            return None
    except Exception as e:
        logger.error(f"컬럼 타입 확인 실패: {e}")
        return None

def migrate_userimage_to_mediumtext():
    """UserImage 컬럼을 MEDIUMTEXT로 변경"""
    try:
        current_type = check_column_type("users", "UserImage")
        
        if current_type is None:
            logger.warning("UserImage 컬럼을 찾을 수 없습니다. 테이블이 아직 생성되지 않았을 수 있습니다.")
            return False
        
        if "mediumtext" in current_type:
            logger.info("✅ UserImage 컬럼이 이미 MEDIUMTEXT 타입입니다.")
            return True
        
        logger.info(f"🔄 UserImage 컬럼 타입 변경 중... (현재: {current_type} → 목표: mediumtext)")
        
        with engine.connect() as connection:
            sql = text("ALTER TABLE users MODIFY COLUMN UserImage MEDIUMTEXT NULL")
            connection.execute(sql)
            connection.commit()
            
        logger.info("✅ UserImage 컬럼이 MEDIUMTEXT로 변경되었습니다.")
        return True
        
    except Exception as e:
        logger.error(f"❌ UserImage 마이그레이션 실패: {e}")
        return False

def init_database():
    """데이터베이스 초기화 (테이블 생성 및 마이그레이션)"""
    try:
        logger.info("=" * 80)
        logger.info("🔧 데이터베이스 초기화 시작")
        logger.info("=" * 80)
        
        # 1. 데이터베이스 연결 테스트
        with engine.connect() as connection:
            logger.info("✅ 데이터베이스 연결 성공")
        
        # 2. Inspector로 기존 테이블 확인
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if not existing_tables:
            logger.info("📝 기존 테이블이 없습니다. 새로 생성합니다...")
        else:
            logger.info(f"📋 기존 테이블: {', '.join(existing_tables)}")
        
        # 3. 테이블 생성 (없는 경우에만)
        Base.metadata.create_all(bind=engine)
        logger.info("✅ 테이블 생성/확인 완료")
        
        # 4. UserImage 컬럼 타입 확인 및 변경
        if "users" in inspector.get_table_names():
            migrate_userimage_to_mediumtext()
        
        logger.info("=" * 80)
        logger.info("✅ 데이터베이스 초기화 완료")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
        logger.error("=" * 80)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 직접 실행 시 (테스트용)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    init_database()
