# Neuroglancer 대용량 뷰어 시스템

대용량 이미지를 Neuroglancer 형식으로 변환하고 웹에서 시각화하는 통합 시스템입니다.

## 🎯 주요 기능

- ✅ **이미지 업로드**: PNG, JPG, TIFF 형식 지원
- ✅ **자동 변환**: Neuroglancer Precomputed 형식으로 자동 변환
- ✅ **메모리 관리**: 실시간 메모리 모니터링 및 최적화
- ✅ **사용자 관리**: 회원가입/로그인 시스템
- ✅ **볼륨 관리**: 변환된 데이터 관리 및 삭제
- ✅ **웹 뷰어**: Neuroglancer 통합 웹 인터페이스

## 📋 요구사항

- Python 3.10 이상
- PostgreSQL (또는 SQLite)
- 8GB RAM 이상 권장

## 🚀 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd 2025_CapstoneDesign_TEAM_3
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가합니다:

```env
# 데이터베이스 설정
DATABASE_URL=postgresql://user:password@localhost/dbname

# 데이터 디렉터리 (선택적)
DATA_DIR=./uploads

# 서버 설정
PORT=8000
```

### 5. 데이터베이스 초기화

```bash
# Alembic 마이그레이션 (있는 경우)
alembic upgrade head
```

### 6. 서버 실행

```bash
python -m app.Services.main
```

또는

```bash
uvicorn app.Services.main:app --host localhost --port 8000 --reload
```

## 📚 API 엔드포인트

### 인증 API (`/v1`)
- `POST /v1/users` - 사용자 생성
- `GET /v1/users/{user_id}` - 사용자 조회
- `PUT /v1/users/{user_id}` - 사용자 수정
- `DELETE /v1/users/{user_id}` - 사용자 삭제

### Neuroglancer API (`/api`)

#### 이미지 업로드
```http
POST /api/upload
Content-Type: multipart/form-data

file: <image-file>
```

**응답 예시:**
```json
{
  "message": "파일이 성공적으로 업로드되고 변환되었습니다.",
  "volume_name": "sample_image",
  "volume_path": "/precomp/sample_image",
  "neuroglancer_url": "precomputed://http://localhost:8000/precomp/sample_image",
  "dimensions": [1024, 768, 1],
  "num_channels": 3,
  "chunk_size": 512
}
```

#### 볼륨 목록 조회
```http
GET /api/volumes
```

**응답 예시:**
```json
{
  "volumes": [
    {
      "name": "sample_image",
      "path": "/precomp/sample_image",
      "info_url": "/precomp/sample_image/info",
      "neuroglancer_url": "precomputed://http://localhost:8000/precomp/sample_image",
      "dimensions": [1024, 768, 1],
      "chunk_size": [512, 512, 1]
    }
  ],
  "count": 1
}
```

#### 볼륨 상세 정보
```http
GET /api/volumes/{volume_name}/info
```

#### 볼륨 삭제
```http
DELETE /api/volumes/{volume_name}
```

### 메모리 관리 API (`/api`)

#### 메모리 상태 조회
```http
GET /api/memory-status
```

**응답 예시:**
```json
{
  "memory": {
    "process_mb": 256.5,
    "system_percent": 45.2,
    "system_available_mb": 8192.0,
    "system_total_mb": 16384.0
  },
  "cache": {
    "cache_size_mb": 50.2,
    "cached_chunks": 120,
    "hit_rate": 0.85
  },
  "config": {
    "cache_max_size_mb": 200,
    "chunk_size": 512
  }
}
```

#### 메모리 정리
```http
POST /api/memory-cleanup
```

#### 시스템 정보 조회
```http
GET /api/system-info
```

## 🖥️ 웹 인터페이스 사용법

1. **브라우저에서 접속**: `http://localhost:8000`

2. **회원가입/로그인**:
   - 회원가입 버튼 클릭
   - 아이디, 비밀번호, 이름, 프로필 사진 입력
   - 로그인

3. **이미지 업로드**:
   - 로그인 후 메인 화면에서 파일 선택
   - "업로드 및 청크 변환" 버튼 클릭
   - 자동으로 Neuroglancer 형식으로 변환됨

4. **볼륨 관리**:
   - 변환된 볼륨 목록에서 확인
   - "Neuroglancer에서 열기" 버튼으로 뷰어 실행
   - URL 복사하여 공유 가능
   - "삭제" 버튼으로 볼륨 제거

5. **메모리 모니터링**:
   - 실시간 메모리 사용량 확인
   - "메모리 정리" 버튼으로 최적화

## 📂 프로젝트 구조

```
2025_CapstoneDesign_TEAM_3/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── Auth.py          # 인증 API
│   │           ├── user.py          # 사용자 API
│   │           ├── neuroglancer.py  # Neuroglancer API
│   │           └── memory.py        # 메모리 관리 API
│   ├── core/                        # 핵심 모델
│   ├── database/                    # 데이터베이스 설정
│   ├── repositories/                # 데이터 접근 계층
│   ├── schemas/                     # Pydantic 스키마
│   └── Services/
│       └── main.py                  # FastAPI 앱 진입점
├── static/
│   ├── css/
│   │   ├── auth.css                # 인증 스타일
│   │   └── common.css              # 공통 스타일
│   ├── js/
│   │   └── app.js                  # 프론트엔드 로직
│   └── index.html                  # 메인 페이지
├── uploads/                        # 업로드된 데이터 (자동 생성)
│   ├── temp/                       # 임시 파일
│   └── {volume_name}/              # 변환된 볼륨
├── alembic/                        # DB 마이그레이션
├── .env                            # 환경 변수
├── requirements.txt                # Python 패키지
└── README.md                       # 이 파일
```

## 🔧 설정

### 청크 크기 조정

`app/api/v1/endpoints/neuroglancer.py`에서 `CHUNK_SIZE` 변수 수정:

```python
CHUNK_SIZE = 512  # 기본값
# CHUNK_SIZE = 256  # 작은 메모리 환경
# CHUNK_SIZE = 1024 # 큰 메모리 환경
```

### 데이터 디렉터리 변경

환경 변수로 설정:

```bash
export DATA_DIR=/path/to/data
```

또는 `.env` 파일에:

```env
DATA_DIR=/path/to/data
```

### 메모리 설정

메모리 관리 파라미터 조정 (향후 구현):

```python
memory_config = MemoryConfig(
    max_image_size_mb=500,
    chunk_size=512,
    cache_max_size_mb=200,
    memory_cleanup_threshold=0.8
)
```

## 🐛 문제 해결

### 1. "파일을 찾을 수 없습니다" 오류

- `uploads/temp` 디렉터리가 존재하는지 확인
- 권한 문제가 있는지 확인
- 서버를 재시작

### 2. 메모리 부족 오류

- `CHUNK_SIZE`를 256으로 줄이기
- 메모리 정리 기능 사용
- 큰 이미지는 분할하여 업로드

### 3. Neuroglancer에서 이미지가 안 보임

- `/precomp/{volume_name}/info` 파일 확인
- CORS 설정 확인
- 브라우저 콘솔에서 에러 확인

### 4. 포트가 이미 사용 중

```bash
# 다른 포트로 실행
uvicorn app.Services.main:app --port 8001
```

## 📝 개발 가이드

### 새로운 API 추가

1. `app/api/v1/endpoints/` 에 새 파일 생성
2. FastAPI 라우터 정의
3. `app/Services/main.py`에 라우터 등록

```python
from app.api.v1.endpoints import new_endpoint

app.include_router(
    new_endpoint.router,
    prefix="/api",
    tags=["NewFeature"]
)
```

### 데이터베이스 모델 추가

1. `app/core/`에 모델 정의
2. Alembic 마이그레이션 생성:

```bash
alembic revision --autogenerate -m "Add new model"
alembic upgrade head
```

### 프론트엔드 수정

- HTML: `static/index.html`
- CSS: `static/css/`
- JavaScript: `static/js/app.js`

## 🧪 테스트

```bash
# API 문서에서 테스트
http://localhost:8000/docs

# 또는 curl 사용
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@test_image.png"
```

## 📄 라이선스

이 프로젝트는 [라이선스 유형]에 따라 배포됩니다.

## 👥 기여자

- Team 3 - Capstone Design 2025

## 📞 문의

문제가 있거나 제안사항이 있으면 Issue를 생성해주세요.

## 🔄 변경 이력

### v2.0.0 (2025-01-XX)
- ✨ Neuroglancer API 통합
- ✨ 메모리 관리 시스템 추가
- ✨ 웹 인터페이스 개선
- 🐛 로그인/메인 화면 병렬 표시 버그 수정

### v1.0.0 (2025-01-XX)
- 🎉 초기 릴리스
- ✨ 사용자 관리 API
- ✨ 기본 웹 인터페이스
