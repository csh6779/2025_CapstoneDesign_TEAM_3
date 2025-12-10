"""
출력 경로 관리 모듈
청크 분해 결과물을 저장할 위치를 관리
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, List


class OutputPathManager:
    """출력 경로 관리자"""

    def __init__(self, default_output_dir: str = None):
        """
        Args:
            default_output_dir: 기본 출력 디렉터리
        """
        self.default_output_dir = default_output_dir
        self.custom_paths = {}  # {volume_name: custom_path}

    def set_default_output_directory(self, output_dir: str) -> bool:
        """
        기본 출력 디렉터리 설정

        Args:
            output_dir: 출력 디렉터리 경로

        Returns:
            성공 여부
        """
        try:
            # 절대 경로로 변환
            output_dir = os.path.abspath(output_dir)

            # 디렉터리 생성
            os.makedirs(output_dir, exist_ok=True)

            # 쓰기 권한 확인
            test_file = os.path.join(output_dir, ".test_write")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)

            self.default_output_dir = output_dir
            print(f"✅ 기본 출력 디렉터리 설정: {output_dir}")
            return True

        except PermissionError:
            print(f"❌ 출력 디렉터리 쓰기 권한 없음: {output_dir}")
            return False
        except Exception as e:
            print(f"❌ 출력 디렉터리 설정 실패: {e}")
            return False

    def get_default_output_directory(self) -> Optional[str]:
        """기본 출력 디렉터리 반환"""
        return self.default_output_dir

    def set_custom_output_path(self, volume_name: str, custom_path: str) -> bool:
        """
        특정 볼륨의 출력 경로를 커스텀 설정

        Args:
            volume_name: 볼륨 이름
            custom_path: 커스텀 출력 경로

        Returns:
            성공 여부
        """
        try:
            custom_path = os.path.abspath(custom_path)
            os.makedirs(custom_path, exist_ok=True)

            # 쓰기 권한 확인
            test_file = os.path.join(custom_path, ".test_write")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)

            self.custom_paths[volume_name] = custom_path
            print(f"✅ 볼륨 '{volume_name}' 출력 경로 설정: {custom_path}")
            return True

        except Exception as e:
            print(f"❌ 커스텀 출력 경로 설정 실패: {e}")
            return False

    def get_output_path(self, volume_name: str, custom_path: Optional[str] = None) -> str:
        """
        볼륨의 최종 출력 경로 결정

        우선순위:
        1. 함수 인자로 전달된 custom_path
        2. 이전에 설정된 custom_paths[volume_name]
        3. default_output_dir

        Args:
            volume_name: 볼륨 이름
            custom_path: 커스텀 출력 경로 (선택)

        Returns:
            최종 출력 경로
        """
        # 1. 함수 인자로 전달된 경로
        if custom_path:
            output_dir = os.path.abspath(custom_path)
            os.makedirs(output_dir, exist_ok=True)
            return os.path.join(output_dir, volume_name)

        # 2. 이전에 설정된 커스텀 경로
        if volume_name in self.custom_paths:
            return os.path.join(self.custom_paths[volume_name], volume_name)

        # 3. 기본 출력 디렉터리
        if self.default_output_dir:
            return os.path.join(self.default_output_dir, volume_name)

        # 기본값 없으면 에러
        raise ValueError(
            f"출력 경로가 설정되지 않았습니다.\n"
            f"다음 중 하나를 설정하세요:\n"
            f"1. custom_path 파라미터 전달\n"
            f"2. set_custom_output_path() 사용\n"
            f"3. set_default_output_directory() 사용"
        )

    def list_custom_paths(self) -> Dict[str, str]:
        """커스텀 설정된 출력 경로 목록"""
        return self.custom_paths.copy()

    def clear_custom_path(self, volume_name: str) -> bool:
        """특정 볼륨의 커스텀 경로 제거"""
        if volume_name in self.custom_paths:
            del self.custom_paths[volume_name]
            print(f"✅ 볼륨 '{volume_name}' 커스텀 경로 제거")
            return True
        return False

    def get_path_info(self, volume_name: str) -> Dict:
        """경로 정보 조회"""
        try:
            final_path = self.get_output_path(volume_name)

            return {
                "volume_name": volume_name,
                "output_path": final_path,
                "is_custom": volume_name in self.custom_paths,
                "default_dir": self.default_output_dir,
                "exists": os.path.exists(final_path)
            }
        except ValueError as e:
            return {
                "volume_name": volume_name,
                "error": str(e)
            }