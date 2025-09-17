# DZI 배치 변환기

`original/` 폴더의 이미지 파일들을 DZI 형식으로 변환하여 `dzi/` 폴더에 저장하는 유틸리티입니다.

## 🚀 빠른 시작

### 1. 기본 실행 (모든 이미지 변환)
```bash
# Windows
run_local.bat

# Linux/Mac
./run_local.sh

# 또는 직접 실행
python batch_dzi_converter.py
```

### 2. 파일 목록만 확인 (실제 변환 없음)
```bash
python batch_dzi_converter.py --dry-run
```

### 3. 고급 옵션으로 실행
```bash
# 4개 작업자로 병렬 처리
python batch_dzi_converter.py --workers 4

# 256x256 타일로 변환
python batch_dzi_converter.py --tile-size 256

# 타일 오버랩 설정
python batch_dzi_converter.py --overlap 1

# 특정 파일만 변환 (확장자 제외 가능)
python batch_dzi_converter.py --file "wafer"
python batch_dzi_converter.py --file "wafer.bmp"

# 특정 파일을 고급 옵션으로 변환
python batch_dzi_converter.py --file "wafer" --workers 4 --tile-size 256
```

## 📁 폴더 구조

```
utility/
├── batch_dzi_converter.py      # 메인 변환 스크립트
├── util_zarr.py               # DZI 변환 라이브러리
├── run_local.bat              # Windows 실행 스크립트
├── run_local.sh               # Linux/Mac 실행 스크립트
├── logs/                      # 로그 파일 저장 폴더
└── README.md                  # 이 파일
```

## ⚙️ 명령행 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--original-dir` | 원본 이미지 폴더 경로 | `../data/uploads/original` |
| `--dzi-dir` | DZI 출력 폴더 경로 | `../data/dzi` |
| `--file` | 변환할 특정 파일명 (확장자 제외 가능) | `None` (모든 파일) |
| `--workers` | 동시 처리할 작업 수 | `2` |
| `--tile-size` | 타일 크기 (픽셀) | `512` |
| `--overlap` | 타일 오버랩 (픽셀) | `0` |
| `--dry-run` | 실제 변환 없이 파일 목록만 출력 | `False` |

## 🔧 지원하는 이미지 형식

- **TIFF**: `.tif`, `.tiff`
- **PNG**: `.png`
- **BMP**: `.bmp`
- **JPEG**: `.jpg`, `.jpeg`

## 📊 성능 최적화

### 작업자 수 조정
```bash
# CPU 코어 수에 따라 조정 (예: 4코어)
python batch_dzi_converter.py --workers 4
```

### 타일 크기 조정
```bash
# 작은 타일: 빠른 로딩, 큰 메모리 사용
python batch_dzi_converter.py --tile-size 256

# 큰 타일: 느린 로딩, 작은 메모리 사용
python batch_dzi_converter.py --tile-size 1024
```

## 📝 로그 확인

변환 과정과 결과는 `logs/dzi_conversion.log` 파일에 저장됩니다:

```bash
# 실시간 로그 확인
tail -f logs/dzi_conversion.log

# Windows에서 로그 확인
type logs\dzi_conversion.log
```

## ❗ 문제 해결

### ImportError 발생 시
1. `util_zarr.py` 파일이 `utility/` 폴더에 있는지 확인
2. Python 환경에 필요한 패키지 설치:
   ```bash
   pip install pillow tifffile zarr numpy
   ```

### 메모리 부족 시
1. `--workers` 수를 줄이기
2. `--tile-size`를 늘리기
3. 한 번에 하나씩 변환하기

### 경로 문제 시
절대 경로로 지정:
```bash
python batch_dzi_converter.py --original-dir "C:\Projects\ATI\example\Zarr-DZI-OSD-sample\web-server\data\uploads\original" --dzi-dir "C:\Projects\ATI\example\Zarr-DZI-OSD-sample\web-server\data\dzi"
```

## 🐳 Docker 사용 (선택사항)

도커를 사용하고 싶다면:

```bash
# 배치 변환
docker-compose -f docker-compose.dzi-converter.yml --profile dzi-convert up --build

# 대화형 모드
docker-compose -f docker-compose.dzi-converter.yml --profile interactive up --build
```
