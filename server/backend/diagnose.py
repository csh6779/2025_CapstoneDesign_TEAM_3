"""
빠른 진단 스크립트
프로젝트가 정상적으로 실행되지 않을 때 사용하세요.
"""
import sys
import os

print("=" * 60)
print("프로젝트 진단 시작")
print("=" * 60)

# 1. Python 버전 확인
print(f"\n1. Python 버전: {sys.version}")

# 2. 현재 디렉터리 확인
print(f"\n2. 현재 디렉터리: {os.getcwd()}")

# 3. 필수 파일 존재 확인
print("\n3. 필수 파일 체크:")
files_to_check = [
    "main.py",
    "requirements.txt",
    "memory_management/__init__.py",
    "memory_management/memory_config.py",
    "memory_management/memory_manager.py",
]

for file in files_to_check:
    exists = os.path.exists(file)
    status = "✓" if exists else "✗"
    print(f"   {status} {file}")

# 4. 필수 모듈 import 테스트
print("\n4. 모듈 import 테스트:")
modules = [
    ("fastapi", "FastAPI"),
    ("uvicorn", "uvicorn"),
    ("PIL", "Pillow"),
    ("numpy", "numpy"),
    ("cloudvolume", "cloud-volume"),
    ("psutil", "psutil"),
]

for module_name, package_name in modules:
    try:
        __import__(module_name)
        print(f"   ✓ {module_name} ({package_name})")
    except ImportError:
        print(f"   ✗ {module_name} ({package_name}) - 설치 필요!")

# 5. memory_management 모듈 import 테스트
print("\n5. memory_management 모듈 테스트:")
try:
    from memory_management import MemoryManager, MemoryConfig
    print("   ✓ memory_management 모듈 import 성공")
    
    # 메모리 관리자 초기화 테스트
    config = MemoryConfig(
        max_image_size_mb=100,
        chunk_size=512,
        cache_max_size_mb=50,
        memory_cleanup_threshold=0.8
    )
    print("   ✓ MemoryConfig 생성 성공")
    
    manager = MemoryManager(config)
    print("   ✓ MemoryManager 초기화 성공")
    
except Exception as e:
    print(f"   ✗ memory_management 오류: {e}")
    import traceback
    traceback.print_exc()

# 6. 디렉터리 구조 확인
print("\n6. 디렉터리 구조:")
dirs_to_check = ["uploads", "uploads/temp", "static"]
for dir_path in dirs_to_check:
    exists = os.path.exists(dir_path)
    status = "✓" if exists else "✗"
    print(f"   {status} {dir_path}")
    if not exists:
        try:
            os.makedirs(dir_path, exist_ok=True)
            print(f"      → 생성 완료!")
        except Exception as e:
            print(f"      → 생성 실패: {e}")

# 7. main.py 문법 체크
print("\n7. main.py 문법 체크:")
try:
    import py_compile
    py_compile.compile('main.py', doraise=True)
    print("   ✓ main.py 문법 오류 없음")
except SyntaxError as e:
    print(f"   ✗ 문법 오류 발견:")
    print(f"      Line {e.lineno}: {e.msg}")
    print(f"      {e.text}")
except Exception as e:
    print(f"   ✗ 체크 실패: {e}")

print("\n" + "=" * 60)
print("진단 완료!")
print("=" * 60)

# 8. 해결 방법 제시
print("\n💡 문제 해결 방법:")
print("\n설치되지 않은 모듈이 있다면:")
print("  pip install -r requirements.txt")
print("\nmemory_management 오류가 있다면:")
print("  cd memory_management")
print("  python -m py_compile *.py")
print("\nPython 경로 문제라면:")
print("  가상환경을 사용하세요:")
print("  python -m venv venv")
print("  venv\\Scripts\\activate  # Windows")
print("  pip install -r requirements.txt")

print("\n자세한 오류 메시지를 확인하려면:")
print("  python main.py")
