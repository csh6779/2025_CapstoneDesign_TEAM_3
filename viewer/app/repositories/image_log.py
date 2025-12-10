"""ImageLog Repository - 이미지 로그 CRUD"""
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from core.ImageLogModel import ImageLog
from schemas.ImageLog import ImageLogCreate, ImageLogUpdate

class ImageLogRepository:
    """이미지 로그 데이터 접근 레이어"""

    def create_log(self, db: Session, user_id: int, payload: ImageLogCreate) -> ImageLog:
        """새로운 이미지 로그 생성"""
        new_log = ImageLog(
            UserId=user_id,
            ImageId=payload.ImageId,
            ChunkCount=payload.ChunkCount,
            ImageSize=payload.ImageSize,
            Status=payload.Status,
            FileBasePath=payload.FileBasePath
        )
        
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        
        return new_log

    def get_log_by_id(self, db: Session, log_id: int) -> Optional[ImageLog]:
        """ID로 로그 조회"""
        return db.query(ImageLog).filter(ImageLog.ImageLogId == log_id).first()

    def get_user_logs(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[ImageLog]:
        """사용자의 모든 로그 조회"""
        return db.query(ImageLog).filter(ImageLog.UserId == user_id)\
            .order_by(ImageLog.CreateAt.desc())\
            .offset(skip).limit(limit).all()

    def get_all_logs(self, db: Session, skip: int = 0, limit: int = 100) -> List[ImageLog]:
        """모든 로그 조회 (관리자용)"""
        return db.query(ImageLog)\
            .order_by(ImageLog.CreateAt.desc())\
            .offset(skip).limit(limit).all()

    def update_log(self, db: Session, log_id: int, payload: ImageLogUpdate) -> Optional[ImageLog]:
        """로그 업데이트"""
        log = db.query(ImageLog).filter(ImageLog.ImageLogId == log_id).first()
        if not log:
            return None
        
        if payload.Status is not None:
            log.Status = payload.Status
        if payload.ChunkCount is not None:
            log.ChunkCount = payload.ChunkCount
        if payload.EndAt is not None:
            log.EndAt = payload.EndAt
        if payload.TotalTime is not None:
            log.TotalTime = payload.TotalTime
        
        db.commit()
        db.refresh(log)
        
        return log

    def complete_log(self, db: Session, log_id: int, total_time: int) -> Optional[ImageLog]:
        """로그 완료 처리"""
        log = db.query(ImageLog).filter(ImageLog.ImageLogId == log_id).first()
        if not log:
            return None
        
        log.Status = "completed"
        log.EndAt = datetime.utcnow()
        log.TotalTime = total_time
        
        db.commit()
        db.refresh(log)
        
        return log

    def fail_log(self, db: Session, log_id: int) -> Optional[ImageLog]:
        """로그 실패 처리"""
        log = db.query(ImageLog).filter(ImageLog.ImageLogId == log_id).first()
        if not log:
            return None
        
        log.Status = "failed"
        log.EndAt = datetime.utcnow()
        
        db.commit()
        db.refresh(log)
        
        return log

    def delete_log(self, db: Session, log_id: int) -> bool:
        """로그 삭제"""
        log = db.query(ImageLog).filter(ImageLog.ImageLogId == log_id).first()
        if log:
            db.delete(log)
            db.commit()
            return True
        return False
