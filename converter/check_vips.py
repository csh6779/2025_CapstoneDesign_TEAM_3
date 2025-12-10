import os
import sys

print("="*40)
print("pyvips 로딩 진단 도구")
print(f"Python 버전: {sys.version}")
print("="*40)

# 1. 경로 확인
vipshome = r'C:\vips-dev-8.17\bin'
print(f"설정된 libvips 경로: {vipshome}")

if os.path.exists(vipshome):
    print("✅ 경로가 실제로 존재합니다.")
    
    # 2. DLL 목록 확인 (핵심 파일 있는지)
    files = os.listdir(vipshome)
    dll_count = len([f for f in files if f.endswith('.dll')])
    print(f"📂 폴더 내 DLL 파일 개수: {dll_count}개")
    
    if 'libvips-42.dll' in files:
        print("✅ 핵심 파일 (libvips-42.dll) 확인됨.")
    else:
        print("❌ 핵심 파일 (libvips-42.dll)이 없습니다! 잘못된 버전을 다운로드했을 수 있습니다.")

    # 3. DLL 경로 추가 시도
    if os.name == 'nt':
        try:
            os.add_dll_directory(vipshome)
            print("✅ os.add_dll_directory() 성공.")
        except Exception as e:
            print(f"❌ os.add_dll_directory() 실패: {e}")

else:
    print("❌ 경로가 존재하지 않습니다! 폴더명이나 위치를 다시 확인하세요.")

print("-" * 40)
print("pyvips import 시도 중...")

# 4. 실제 import 시도 (에러를 숨기지 않음)
try:
    import pyvips
    print("\n🎉 성공! pyvips가 정상적으로 로드되었습니다.")
    print(f"pyvips 버전: {pyvips.__version__}")
except Exception as e:
    print("\n💥 실패! 에러 메시지를 확인하세요:")
    print("=" * 40)
    import traceback
    traceback.print_exc()
    print("=" * 40)
    print("\n[힌트] 'DLL load failed' 에러라면 -> 의존성 파일 부족 또는 VC++ 런타임 누락")
    print("[힌트] 'ModuleNotFoundError' 에러라면 -> pip install pyvips 안됨")

input("\n종료하려면 엔터키를 누르세요...")