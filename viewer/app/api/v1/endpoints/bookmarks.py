"""북마크 API"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database.database import get_db
from core.Jwt import get_current_user
from core.UserModel import User
from repositories.bookmark import BookmarkRepository
from schemas.Bookmarks import BookmarkCreate, BookmarkUpdate, BookmarkResponse

router = APIRouter(prefix="/bookmarks", tags=["북마크"])

bookmark_repo = BookmarkRepository()

@router.post("/", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    payload: BookmarkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """북마크 생성"""
    new_bookmark = bookmark_repo.create_bookmark(db, current_user.id, payload)
    return new_bookmark

@router.get("/me", response_model=List[BookmarkResponse])
async def get_my_bookmarks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """내 북마크 목록 조회"""
    bookmarks = bookmark_repo.get_user_bookmarks(db, current_user.id, skip, limit)
    return bookmarks

@router.get("/{bookmark_id}", response_model=BookmarkResponse)
async def get_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 북마크 조회"""
    bookmark = bookmark_repo.get_bookmark_by_id(db, bookmark_id)
    
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="북마크를 찾을 수 없습니다."
        )
    
    # 본인의 북마크인지 확인
    if bookmark.UserId != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="접근 권한이 없습니다."
        )
    
    return bookmark

@router.put("/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(
    bookmark_id: int,
    payload: BookmarkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """북마크 수정"""
    # 소유권 확인
    if not bookmark_repo.check_bookmark_ownership(db, bookmark_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인의 북마크만 수정할 수 있습니다."
        )
    
    updated_bookmark = bookmark_repo.update_bookmark(db, bookmark_id, payload)
    if not updated_bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="북마크를 찾을 수 없습니다."
        )
    
    return updated_bookmark

@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """북마크 삭제"""
    # 소유권 확인
    if not bookmark_repo.check_bookmark_ownership(db, bookmark_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="본인의 북마크만 삭제할 수 있습니다."
        )
    
    success = bookmark_repo.delete_bookmark(db, bookmark_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="북마크를 찾을 수 없습니다."
        )
    
    return None
