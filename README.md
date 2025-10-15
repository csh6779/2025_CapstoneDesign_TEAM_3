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
- MySQL 8.0 이상
- 8GB RAM 이상 권장
- pip (Python 패키지 관리자)

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

### 4. 데이터베이스 설정

#### MySQL 데이터베이스 생성

```sql
CREATE DATABASE capstone CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 수정합니다:

```bash
cp .env.example .env
```

`.env` 파일 내용:

```env
# 데이터베이스 설정
DB_USER=root
DB_PASSWORD=1234
DB_HOST=localhost
DB_PORT=3306
DB_NAME=capstone

# JWT 설정
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# 애플리케이션 설정
APP_NAME=Capstone Project
DEBUG=True

# 파일 업로드 설정
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE=10485760
```

### 5. 데이터베이스 마이그레이션

#### 자동 설정 (Windows)

```bash
setup.bat
```

#### 자동 설정 (Linux/Mac)

```bash
chmod +x setup.sh
./setup.sh
```

#### 수동 설정

```bash
# 1. 데이터베이스 연결 테스트
python -c "from app.database.database import test_connection; test_connection()"

# 2. 마이그레이션 파일 생성
alembic revision --autogenerate -m "Initial migration"

# 3. 마이그레이션 적용
alembic upgrade head

# 4. 현재 마이그레이션 상태 확인
alembic current
```

### 6. 서버 실행

#### Windows

```bash
start_server.bat
```

#### Linux/Mac

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

또는

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

서버 실행 후 다음 URL에서 접속:
- 메인 페이지: http://localhost:8000
- API 문서: http://localhost:8000/docs
- Alternative API 문서: http://localhost:8000/redoc

## 📚 API 엔드포인트

### 인증 API (`/api/v1/auth`)

#### 로그인
```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=your_login_id&password=your_password
```

**응답:**
```json
{
  "AccessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "TokenType": "bearer",
  "ExpiresInMin": 30
}
```

### 사용자 API (`/api/v1/users`)

#### 회원가입
```http
POST /api/v1/users/signup
Content-Type: application/json

{
  "LoginId": "user123",
  "Password": "password123",
  "UserName": "홍길동",
  "Role": "user"
}
```

#### 내 정보 조회
```http
GET /api/v1/users/me
Authorization: Bearer {access_token}
```

#### 사용자 정보 수정
```http
PUT /api/v1/users/{user_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "UserName": "새이름",
  "UserImage": "profile.jpg"
}
```

#### 사용자 삭제 (관리자)
```http
DELETE /api/v1/users/{user_id}
Authorization: Bearer {access_token}
```

### 이미지 로그 API (`/api/v1/image-logs`)

#### 이미지 로그 생성
```http
POST /api/v1/image-logs/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "UserId": 1,
  "ImageId": "img_20250115_001",
  "ChunkCount": 128,
  "ImageSize": 5120,
  "Status": "pending",
  "FileBasePath": "/uploads/images"
}
```

#### 내 로그 조회
```http
GET /api/v1/image-logs/me?skip=0&limit=100
Authorization: Bearer {access_token}
```

#### 로그 완료 처리
```http
POST /api/v1/image-logs/{log_id}/complete
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "total_time": 450
}
```

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
├── alembic/                         # DB 마이그레이션
│   ├── versions/                    # 마이그레이션 파일들
│   ├── env.py                       # Alembic 환경 설정
│   └── script.py.mako
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── Auth.py          # 인증 API (JWT)
│   │           ├── user.py          # 사용자 관리 API
│   │           ├── logs.py          # 이미지 로그 API
│   │           ├── neuroglancer.py  # Neuroglancer API
│   │           └── memory.py        # 메모리 관리 API
│   ├── core/
│   │   ├── UserModel.py             # User DB 모델
│   │   ├── ImageLogModel.py         # ImageLog DB 모델
│   │   └── Jwt.py                   # JWT 토큰 처리
│   ├── database/
│   │   └── database.py              # DB 연결 및 세션 관리
│   ├── repositories/
│   │   ├── user.py                  # User Repository
│   │   ├── image_log.py             # ImageLog Repository
│   │   └── __init__.py
│   ├── schemas/
│   │   ├── Users.py                 # User Pydantic 스키마
│   │   └── ImageLog.py              # ImageLog Pydantic 스키마
│   ├── Services/
│   │   └── main.py                  # FastAPI 앱 진입점
│   └── utils/                       # 유틸리티 함수
├── static/
│   ├── css/
│   │   ├── auth.css                # 인증 스타일
│   │   └── common.css              # 공통 스타일
│   ├── js/
│   │   └── app.js                  # 프론트엔드 로직
│   └── index.html                  # 메인 페이지
├── logs/                           # 애플리케이션 로그
├── static/
│   ├── css/
│   │   ├── auth.css                # 인증 페이지 스타일
│   │   └── common.css              # 공통 스타일
│   ├── js/
│   │   └── app.js                  # 프론트엔드 로직
│   └── index.html                  # 메인 페이지
├── uploads/                        # 업로드된 데이터 (자동 생성)
│   ├── temp/                       # 임시 파일
│   └── {volume_name}/              # 변환된 볼륨
├── .env                            # 환경 변수 (git 제외)
├── .env.example                    # 환경 변수 템플릿
├── .gitignore
├── alembic.ini                     # Alembic 설정
├── requirements.txt                # Python 패키지
├── setup.bat                       # Windows 설정 스크립트
├── setup.sh                        # Linux/Mac 설정 스크립트
├── start_server.bat                # Windows 서버 실행
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

### 1. "No module named 'pymysql'" 오류

```bash
pip install pymysql
```

### 2. 데이터베이스 연결 실패

- MySQL 서버가 실행 중인지 확인
- `.env` 파일의 DB 설정 확인 (사용자명, 비밀번호, 포트)
- MySQL에서 데이터베이스가 생성되었는지 확인

```sql
SHOW DATABASES LIKE 'capstone';
```

### 3. "Target database is not up to date" 오류

```bash
alembic upgrade head
```

### 4. "Table already exists" 오류

```bash
# 기존 테이블 삭제 후 재생성 (주의: 데이터 손실)
alembic downgrade base
alembic upgrade head
```

### 5. JWT 토큰 오류

- `.env` 파일의 `JWT_SECRET_KEY` 확인
- 토큰이 만료되었는지 확인 (기본 30분)
- 다시 로그인하여 새 토큰 발급

### 6. "파일을 찾을 수 없습니다" 오류

- `uploads/temp` 디렉터리가 존재하는지 확인
- 권한 문제가 있는지 확인
- 서버를 재시작

### 7. 메모리 부족 오류

- `CHUNK_SIZE`를 256으로 줄이기
- 메모리 정리 기능 사용
- 큰 이미지는 분할하여 업로드

### 8. Neuroglancer에서 이미지가 안 보임

- `/precomp/{volume_name}/info` 파일 확인
- CORS 설정 확인
- 브라우저 콘솔에서 에러 확인

### 9. 포트가 이미 사용 중

```bash
# 다른 포트로 실행
uvicorn app.main:app --port 8001
```

### 10. Alembic 마이그레이션 충돌

```bash
# 현재 상태 확인
alembic current

# 마이그레이션 히스토리 확인
alembic history

# 특정 버전으로 이동
alembic upgrade <revision_id>
```

## 📝 개발 가이드

### 데이터베이스 스키마 변경

1. **모델 수정**: `app/core/`에서 SQLAlchemy 모델 수정
2. **스키마 수정**: `app/schemas/`에서 Pydantic 스키마 수정
3. **마이그레이션 생성**:

```bash
alembic revision --autogenerate -m "변경 내용 설명"
```

4. **마이그레이션 적용**:

```bash
alembic upgrade head
```

5. **마이그레이션 롤백** (필요시):

```bash
alembic downgrade -1  # 한 단계 이전
```

### 새로운 API 엔드포인트 추가

1. **엔드포인트 파일 생성**: `app/api/v1/endpoints/new_feature.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.database import get_db

router = APIRouter(
    prefix="/new-feature",
    tags=["New Feature"]
)

@router.get("/")
async def get_items(db: Session = Depends(get_db)):
    # 로직 구현
    return {"message": "Hello"}
```

2. **라우터 등록**: `app/main.py`에 추가

```python
from app.api.v1.endpoints import new_feature

app.include_router(
    new_feature.router,
    prefix="/api/v1",
    tags=["New Feature"]
)
```

### Repository 패턴 사용

1. **Repository 클래스 생성**: `app/repositories/new_repo.py`

```python
from sqlalchemy.orm import Session
from app.core.NewModel import NewModel

class NewRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self):
        return self.db.query(NewModel).all()
```

2. **엔드포인트에서 사용**:

```python
from app.repositories import NewRepository

@router.get("/")
async def get_items(db: Session = Depends(get_db)):
    repo = NewRepository(db)
    items = repo.get_all()
    return items
```

### JWT 인증 보호 엔드포인트

```python
from app.core.Jwt import get_current_user
from app.schemas.Users import User

@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_user)
):
    return {"message": f"Hello {current_user.UserName}"}
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

## 🔐 보안 고려사항

### 프로덕션 배포 시

1. **환경 변수 보안**
   - `.env` 파일을 Git에 커밋하지 않기
   - 강력한 `JWT_SECRET_KEY` 사용
   - 데이터베이스 비밀번호 변경

2. **HTTPS 사용**
   - 프로덕션에서는 반드시 HTTPS 사용
   - Let's Encrypt로 무료 SSL 인증서 발급

3. **CORS 설정**
   - 신뢰할 수 있는 도메인만 허용

4. **Rate Limiting**
   - 로그인 API에 속도 제한 적용
   - DDoS 공격 방지

5. **SQL Injection 방지**
   - SQLAlchemy ORM 사용으로 기본 방지됨
   - Raw SQL 쿼리 사용 자제

6. **비밀번호 정책**
   - 최소 8자 이상
   - 대소문자, 숫자, 특수문자 조합 권장

## 📊 데이터베이스 스키마

### Users 테이블

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| id | INT | PK, AI | 사용자 ID |
| LoginId | VARCHAR(50) | UNIQUE, NOT NULL | 로그인 ID |
| PasswordHash | VARCHAR(255) | NOT NULL | 해시된 비밀번호 |
| UserName | VARCHAR(30) | NOT NULL | 사용자 이름 |
| Role | VARCHAR(10) | DEFAULT 'user' | 권한 (user/admin) |
| UserImage | VARCHAR(255) | NULL | 프로필 이미지 경로 |

### ImageLog 테이블

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| ImageLogId | INT | PK, AI | 로그 ID |
| UserId | INT | FK, NOT NULL | 사용자 ID |
| ImageId | VARCHAR(100) | NULL | 이미지 고유 ID |
| ChunkCount | INT | NULL | 청크 개수 |
| ImageSize | INT | NULL | 이미지 크기 (KB) |
| CreateAt | DATETIME | DEFAULT NOW() | 생성 시각 |
| EndAt | DATETIME | NULL | 완료 시각 |
| Status | VARCHAR(20) | DEFAULT 'pending' | 상태 |
| FileBasePath | VARCHAR(255) | NULL | 파일 경로 |
| TotalTime | INT | NULL | 총 처리 시간 (ms) |

**관계:**
- ImageLog.UserId → Users.id (FK, CASCADE DELETE)

## 📈 성능 최적화

### 데이터베이스 최적화

1. **인덱스 활용**
   - LoginId, UserId, Status 컬럼에 인덱스 적용됨

2. **연결 풀 설정**
   ```python
   # database.py에서 조정 가능
   engine = create_engine(
       SQLALCHEMY_DATABASE_URL,
       pool_size=10,
       max_overflow=20
   )
   ```

3. **쿼리 최적화**
   - Pagination 사용 (skip, limit)
   - 필요한 컬럼만 조회
   - JOIN 최소화

### 메모리 최적화

1. **청크 크기 조정**: 메모리에 따라 CHUNK_SIZE 변경
2. **캐시 관리**: 정기적인 메모리 정리
3. **대용량 파일**: 스트리밍 처리

## 👥 기여자

- Team 3 - Capstone Design 2025

## 📄 라이선스

This project is licensed under the MIT License.

## 📞 문의

문제가 발생하거나 질문이 있으시면 Issue를 등록해주세요.


