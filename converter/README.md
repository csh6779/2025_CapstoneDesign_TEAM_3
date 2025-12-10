# Precomputed Converter - 간단한 CLI 버전

## 📋 개요

이미지 파일을 Neuroglanger Precomputed 형식으로 변환하는 간단한 CLI 도구입니다.


### Python 3.12 버전을 사용해야 라이브러리 사용이 가능합니다.


## 🚀 빠른 시작

### 0. Python 3.12.x 설치(현재 파이썬 버전이 높다면)

```powershell
# 만약 버전이 3.12 가 아니라면 사이트에서 해당 버전 설치 필요
python --version
```

https://www.python.org/downloads/windows/

Windows 버전에 맞는 3.12.x 파이썬 파일을 다운로드합니다.

설치 시 'Add python.exe to PATH' 옵션을 반드시 선택하고 설치를 진행합니다. 
(다른 Python 버전과 충돌을 피하기 위해 기본 설치 경로를 유지하는 것이 좋습니다.)



### 1. 의존성 설치

```powershell
# 가상 환경 생성(/converter 디렉토리 내에서 cmd 오픈)
cd {내 경로}\ati_lab_2025\converter
python -m venv .venv

# 가상 환경 활성화
.\.venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

**참고**: pyvips는 선택사항입니다. libvips DLL이 필요하며, 없으면 자동으로 Pillow를 사용합니다.

### 2. 출력 디렉토리 설정

`output_directory.txt` 파일을 편집하여 출력 루트 디렉토리를 설정:

```
F:/neuroglancer_output
```

### 3. 실행

```powershell
# /converter 디렉토리에서
starter.bat
```

## 💡 사용 방법

### 실행 흐름

1. **프로그램 시작**
   ```
   ============================================================
   Precomputed Converter - CLI
   ============================================================
   
   출력 루트 디렉토리: F:/neuroglancer_output
   pyvips 사용 가능: ✅ Yes
   ============================================================
   ```

2. **파일 경로 입력**
   ```
   변환하고 싶은 파일의 경로를 알려주세요: E:\data\image.bmp
   ```

3. **변환 정보 확인**
   ```
   ============================================================
   변환 정보
   ============================================================
   파일: image.bmp
   크기: 5.23 GB
   변환 대상 폴더: F:/neuroglancer_output/image
   예상 청크 수: 12544
   예상 변환 시간: 약 2시간 30분
   ============================================================
   ```

4. **변환 시작 확인**
   ```
   변환을 시작할까요? [y/n]: y
   ```
   - `y`: 변환 시작
   - `n`: 다시 파일 경로 입력

5. **변환 진행**
   ```
   ============================================================
   변환 시작
   ============================================================
   
   진행률: 45.2% | 청크: 5670/12544 | 처리: 2.36 GB/5.23 GB | 경과: 1시간 8분 | 예상 남은 시간: 1시간 22분
   ```

6. **변환 완료**
   ```
   총 소요 시간: 2시간 15분
   처리된 청크: 12544
   처리된 크기: 5.23 GB
   
   ============================================================
   ✅ 프로세스가 완료되었습니다!
   ============================================================
   출력 위치: F:/neuroglancer_output/image
   
   [아무 키를 눌러 종료해주세요]
   ```

## 📁 파일 구조

```
converter/
├── precomputed_writer.py    # 메인 변환 스크립트
├── starter.bat               # 시작 배치 파일
├── requirements.txt          # Python 의존성
├── output_directory.txt      # 출력 루트 디렉토리 설정
└── README.md                 # 이 파일
```

## 🎯 주요 기능

### 자동 진행률 표시
- 실시간 진행률 (%)
- 현재 청크 / 총 청크
- 처리된 크기 / 총 크기
- 경과 시간
- 예상 남은 시간

### 지능형 예상 시간 계산
- 파일 크기 기반 예상
- pyvips 사용 여부에 따라 조정
- 실시간 진행률 기반 재계산

### pyvips 자동 fallback
- pyvips 사용 가능 시: 빠른 처리 (70% 메모리 감소)
- pyvips 없음: 자동으로 Pillow 사용

## 🔧 설정

### 출력 디렉토리 변경

`output_directory.txt` 파일 편집:
```
F:/uploads
```

### 청크 크기 변경 (고급)

`precomputed_writer.py` 파일에서:
```python
chunk_size=512  # 기본값
# 더 크게: 1024 (빠르지만 메모리 많이 사용)
# 더 작게: 256 (느리지만 메모리 적게 사용)
```

## 📊 지원 형식

| 형식 | 지원 | pyvips | Pillow |
|------|------|--------|--------|
| BMP  | ✅   | ✅     | ✅     |
| PNG  | ✅   | ✅     | ✅     |
| JPG  | ✅   | ✅     | ✅     |
| TIFF | ❌   | -      | -      |

**참고**: TIFF 지원은 원본 파일에 있지만 이 간소화 버전에서는 제외되었습니다.

## 🐛 문제 해결

### Q1: "ModuleNotFoundError: No module named 'pyvips'"

```commandline
============================================================
Precomputed Converter - CLI
============================================================
출력 루트 디렉토리: E:\GithubRepository\Projects\ati_lab_2025\converter\uploads
pyvips 사용 가능: ❌ No (Pillow fallback)
============================================================
변환하고 싶은 파일의 경로를 알려주세요:
```

만약 위와 같이 pyvips가 비활성화 되어 있다면:
- 환경 변수 PATH에 libvips DLL 경로가 설정되어야 함

1. 환경 변수 설정(관리자 권한으로 접속한 PowerShell)

```powershell
[Environment]::SetEnvironmentVariable("PATH", "C:\vips-dev-8.17\bin;" + [Environment]::GetEnvironmentVariable("PATH", "Machine"), "Machine")
```
설정 후 PowerShell을 완전히 닫고 다시 시작해야 함.

2. 환경 변수 확인

```powershell
# PATH 확인
$env:PATH
# C:\vips-dev-8.17\bin 이 포함되어 있는지 확인
```

3. DLL 파일 확인
```powershell
# libvips DLL이 있는지 확인
Test-Path C:\vips-dev-8.17\bin\libvips-42.dll
# True가 나와야 함

# 디렉토리 내용 확인
dir C:\vips-dev-8.17\bin\
```
libvips DLL이 True 라면 정상적으로 실행 될 것이다.


```powershell
# pyvips 설치 (선택사항)
pip install pyvips==2.2.1

# 또는 pyvips 없이 사용 (자동 fallback)
# 에러 메시지 무시하고 계속 실행됨
```



### Q2: "libvips-42.dll not found"

pyvips를 사용하려면 libvips DLL이 필요합니다:
1. https://github.com/libvips/build-win64-mxe/releases
2. 최신 vips-dev-w64-all-*.zip 다운로드
3. C:\vips에 압축 해제
4. 환경 변수 PATH에 C:\vips\bin 추가

**또는** pyvips 없이 사용하세요 (자동으로 Pillow 사용).

### Q3: "파일을 찾을 수 없습니다"

- 경로에 따옴표 제거: `"E:\data\image.bmp"` → `E:\data\image.bmp`
- 역슬래시 사용: `E:\data\image.bmp` 또는 `E:/data/image.bmp`

### Q4: 진행률이 멈춤

- 대용량 파일은 청크 처리 시간이 오래 걸릴 수 있습니다
- 청크 크기를 늘리면 더 빠르게 진행됩니다 (메모리 더 사용)

## 📈 성능

| 파일 크기 | pyvips | Pillow | 차이 |
|-----------|--------|--------|------|
| 1GB      | ~30초  | ~1.5분 | 3x   |
| 10GB     | ~5분   | ~15분  | 3x   |
| 90GB     | ~45분  | ~2시간 | 2.7x |

**권장**: 대용량 파일(>5GB)은 pyvips 사용 권장

## 🎓 사용 팁

### 팁 1: 드래그 앤 드롭
```powershell
# CMD에서
cd E:\GithubRepository\Projects\ati_lab_2025\converter
python -m precomputed_writer

# 그리고 파일을 CMD 창에 드래그하면 경로 자동 입력됨
```

### 팁 2: 배치 처리
여러 파일을 순서대로 처리하려면 각 파일마다 프로그램을 재실행하세요.

### 팁 3: 진행 중 중단
- `Ctrl+C`로 언제든 중단 가능
- 부분적으로 생성된 파일은 수동으로 삭제해야 합니다

