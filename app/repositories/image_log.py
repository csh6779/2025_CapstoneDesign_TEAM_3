# app/repositories/image_log.py

from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.ImageLogModel import ImageLog as ImageLogModel
from app.schemas.ImageLog import ImageLogCreate, ImageLogUpdate, ImageLog

class ImageLogRepository:
    """ImageLog 데이터를 관리하는 Repository 클래스"""

    def __init__(self, db: Session):
        self.db = db

    def create_image_log(self, log_data: ImageLogCreate) -> ImageLog:
        """새로운 이미지 로그 생성"""
        new_log = ImageLogModel(
            UserId=log_data.UserId,
            ImageId=log_data.ImageId,
            ChunkCount=log_data.ChunkCount,
            ImageSize=log_data.ImageSize,
            Status=log_data.Status or "pending",
            FileBasePath=log_data.FileBasePath,
            CreateAt=datetime.utcnow()
        )
        
        self.db.add(new_log)
        self.db.commit()
        self.db.refresh(new_log)
        
        return ImageLog.model_validate(new_log)

    def get_image_log_by_id(self, log_id: int) -> Optional[ImageLog]:
        """ID로 이미지 로그 조회"""
        log = self.db.query(ImageLogModel).filter(ImageLogModel.ImageLogId == log_id).first()
        if log:
            return ImageLog.model_validate(log)
        return None

    def get_logs_by_user_id(self, user_id: int, skip: int = 0, limit: int = 100) -> List[ImageLog]:
        """특정 사용자의 이미지 로그 조회"""
        logs = (
            self.db.query(ImageLogModel)
            .filter(ImageLogModel.UserId == user_id)
            .order_by(ImageLogModel.CreateAt.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [ImageLog.model_validate(log) for log in logs]

    def get_all_logs(self, skip: int = 0, limit: int = 100) -> List[ImageLog]:
        """모든 이미지 로그 조회"""
        logs = (
            self.db.query(ImageLogModel)
            .order_by(ImageLogModel.CreateAt.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [ImageLog.model_validate(log) for log in logs]

    def update_image_log(self, log_id: int, update_data: ImageLogUpdate) -> Optional[ImageLog]:
        """이미지 로그 업데이트"""
        log = self.db.query(ImageLogModel).filter(ImageLogModel.ImageLogId == log_id).first()
        if not log:
            return None
        
        # 업데이트할 필드만 적용
        update_fields = update_data.model_dump(exclude_unset=True)
        
        for field, value in update_fields.items():
            setattr(log, field, value)
        
        self.db.commit()
        self.db.refresh(log)
        
        return ImageLog.model_validate(log)

    def delete_image_log(self, log_id: int) -> bool:
        """이미지 로그 삭제"""
        log = self.db.query(ImageLogModel).filter(ImageLogModel.ImageLogId == log_id).first()
        if log:
            self.db.delete(log)
            self.db.commit()
            return True
        return False

    def get_logs_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[ImageLog]:
        """상태별 이미지 로그 조회"""
        logs = (
            self.db.query(ImageLogModel)
            .filter(ImageLogModel.Status == status)
            .order_by(ImageLogModel.CreateAt.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [ImageLog.model_validate(log) for log in logs]

    def complete_image_log(self, log_id: int, total_time: int) -> Optional[ImageLog]:
        """이미지 처리 완료 상태로 업데이트"""
        log = self.db.query(ImageLogModel).filter(ImageLogModel.ImageLogId == log_id).first()
        if not log:
            return None
        
        log.Status = "completed"
        log.EndAt = datetime.utcnow()
        log.TotalTime = total_time
        
        self.db.commit()
        self.db.refresh(log)
        
        return ImageLog.model_validate(log)

    def fail_image_log(self, log_id: int) -> Optional[ImageLog]:
        """이미지 처리 실패 상태로 업데이트"""
        log = self.db.query(ImageLogModel).filter(ImageLogModel.ImageLogId == log_id).first()
        if not log:
            return None
        
        log.Status = "failed"
        log.EndAt = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(log)
        
        return ImageLog.model_validate(log)
