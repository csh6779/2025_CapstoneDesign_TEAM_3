"""Bookmark Repository - 북마크 CRUD"""
from sqlalchemy.orm import Session
from typing import List, Optional

from core.BookmarkModel import Bookmark
from schemas.Bookmarks import BookmarkCreate, BookmarkUpdate

class BookmarkRepository:
    """북마크 데이터 접근 레이어"""

    def create_bookmark(self, db: Session, user_id: int, payload: BookmarkCreate) -> Bookmark:
        """새로운 북마크 생성"""
        new_bookmark = Bookmark(
            UserId=user_id,
            VolumeName=payload.VolumeName,
            VolumeUrl=payload.VolumeUrl,
            Title=payload.Title or payload.VolumeName,  # 제목이 없으면 볼륨 이름 사용
            Description=payload.Description
        )
        
        db.add(new_bookmark)
        db.commit()
        db.refresh(new_bookmark)
        
        return new_bookmark

    def get_bookmark_by_id(self, db: Session, bookmark_id: int) -> Optional[Bookmark]:
        """ID로 북마크 조회"""
        return db.query(Bookmark).filter(Bookmark.BookmarkId == bookmark_id).first()

    def get_user_bookmarks(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Bookmark]:
        """사용자의 모든 북마크 조회"""
        return db.query(Bookmark).filter(Bookmark.UserId == user_id).offset(skip).limit(limit).all()

    def update_bookmark(self, db: Session, bookmark_id: int, payload: BookmarkUpdate) -> Optional[Bookmark]:
        """북마크 업데이트"""
        bookmark = db.query(Bookmark).filter(Bookmark.BookmarkId == bookmark_id).first()
        if not bookmark:
            return None
        
        if payload.Title is not None:
            bookmark.Title = payload.Title
        if payload.Description is not None:
            bookmark.Description = payload.Description
        
        db.commit()
        db.refresh(bookmark)
        
        return bookmark

    def delete_bookmark(self, db: Session, bookmark_id: int) -> bool:
        """북마크 삭제"""
        bookmark = db.query(Bookmark).filter(Bookmark.BookmarkId == bookmark_id).first()
        if bookmark:
            db.delete(bookmark)
            db.commit()
            return True
        return False

    def check_bookmark_ownership(self, db: Session, bookmark_id: int, user_id: int) -> bool:
        """북마크 소유권 확인"""
        bookmark = db.query(Bookmark).filter(
            Bookmark.BookmarkId == bookmark_id,
            Bookmark.UserId == user_id
        ).first()
        return bookmark is not None
