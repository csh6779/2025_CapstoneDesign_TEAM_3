# app/repositories/user.py

from typing import List, Dict, Any, Optional
from app.schemas.user import UserCreate, UserUpdate, User

# 데이터베이스를 대신할 메모리 저장소
# { user_id: {id: 1, username: "...", email: "...", password: "..."} }
_USERS_DB: Dict[int, Dict[str, Any]] = {}
_NEXT_ID = 1

class UserRepository:
    """
    User 데이터를 관리하는 클래스 (실제 환경에서는 DB와의 상호작용을 처리)
    """

    def create_user(self, user_data: UserCreate) -> User:
        """새로운 사용자 생성"""
        global _NEXT_ID
        
        # 데이터베이스에 저장될 데이터 생성
        new_user = user_data.model_dump() # Pydantic v2
        # new_user = user_data.dict() # Pydantic v1
        new_user["id"] = _NEXT_ID
        
        _USERS_DB[_NEXT_ID] = new_user
        _NEXT_ID += 1
        
        # 응답 스키마(User)에 맞게 변환하여 반환
        return User.model_validate(new_user)

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        user_data = _USERS_DB.get(user_id)
        if user_data:
            return User.model_validate(user_data)
        return None

    def get_all_users(self) -> List[User]:
        """모든 사용자 조회"""
        return [User.model_validate(data) for data in _USERS_DB.values()]

    def update_user(self, user_id: int, update_data: UserUpdate) -> Optional[User]:
        """사용자 정보 업데이트"""
        user_data = _USERS_DB.get(user_id)
        if not user_data:
            return None
        
        # 업데이트할 필드만 병합
        update_fields = update_data.model_dump(exclude_unset=True)
        # update_fields = update_data.dict(exclude_unset=True)
        
        user_data.update(update_fields)
        
        return User.model_validate(user_data)

    def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        if user_id in _USERS_DB:
            del _USERS_DB[user_id]
            return True
        return False