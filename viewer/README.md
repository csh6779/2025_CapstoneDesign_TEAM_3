# ATI Lab 2025 - Neuroglancer Viewer v3.0

대용량 의료 영상 데이터를 위한 웹 기반 3D 뷰어 시스템

## 🌟 주요 특징

### ✅ 인증 시스템
- **JSON 기반 사용자 관리** (MySQL 제거, 경량화)
- **JWT 토큰 인증** (24시간 유효)
- **역할 기반 권한** (관리자/일반 사용자)
- **bcrypt 비밀번호 암호화**

### ✅ 통합 데이터셋 뷰어
- **세 위치 통합 표시**: Converter, F Drive, Tmp
- **실시간 볼륨 스캔**: Precomputed 형식 자동 감지
- **위치별 필터링**: 각 저장소별 데이터셋 관리
- **메타데이터 표시**: 해상도, 크기, 채널 정보

### ✅ 관리자 기능
- **이미지 업로드 & 변환**: TIFF/PNG/JPG → Precomputed 형식
- **자동 청크 변환**: 512x512 청크로 자동 분할
- **볼륨 삭제**: 관리자 전용 삭제 기능
- **메모리 모니터링**: 실시간 시스템 상태 확인

### ✅ 로깅 시스템
- **사용자별 로그 추적**: 개인별 활동 기록
- **JSON 형식 저장**: 구조화된 로그 데이터
- **날짜/레벨 필터링**: 효율적인 로그 검색
- **실시간 조회**: 웹 UI에서 로그 확인

### ✅ Neuroglancer 통합
- **WebGL 3D 렌더링**: 고성능 시각화
- **다중 해상도 지원**: 피라미드 스케일
- **실시간 좌표 표시**: 현재 위치 추적
- **북마크 기능**: 관심 영역 저장

---

## 🚀 빠른 시작

### 1. 시스템 요구사항

- Docker & Docker Compose
- Windows 10/11 (WSL2 필수)
- 8GB RAM 이상 권장
- F 드라이브 접근 권한

### 2. 설치 및 실행

```bash
# 1. 디렉터리 이동
cd E:\GithubRepository\Projects\ati_lab_2025\viewer

# 2. entrypoint.sh 라인 엔딩 수정 (PowerShell)
$file = "entrypoint.sh"
$text = [IO.File]::ReadAllText($file)
$text = $text -replace "`r`n", "`n"
[IO.File]::WriteAllText($file, $text)

# 3. 데이터 디렉터리 생성
New-Item -ItemType Directory -Force -Path ".\data"

# 4. Docker 빌드 및 실행
docker-compose build --no-cache
docker-compose up -d

# 5. 로그 확인
docker-compose logs -f backend
```

### 3. 접속

- **메인 페이지**: http://localhost:9000
- **로그인**: 기본 계정 `admin` / `admin1234`
- **API 문서**: http://localhost:9000/docs

---

## 📁 시스템 구조

### 디렉터리 구조

```
viewer/
├── app/
│   ├── main.py                    # FastAPI 메인 애플리케이션
│   ├── shared_logging.py          # 로깅 시스템
│   └── precomputed_writer.py      # 이미지 변환 유틸리티
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── LoginPage.jsx      # 로그인
│       │   ├── MainPage.jsx       # 메인 뷰어
│       │   ├── Adminpage_static.jsx   # 관리자
│       │   └── LogHistoryPage.jsx # 로그 조회
│       └── index.js
├── data/
│   ├── users.json                 # 사용자 데이터
│   └── bookmarks.json             # 북마크 데이터
├── logs/
│   └── 2025/12/08.txt            # 날짜별 로그
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── entrypoint.sh
```

### 데이터 저장 위치

```
/mnt/converter_uploads      # Converter 서비스에서 변환된 데이터
/mnt/f_uploads              # F 드라이브 (F:/uploads)
/mnt/tmp_uploads            # 관리자 페이지에서 업로드된 데이터
/viewer/data                # 사용자/북마크 JSON 파일
/logs                       # 애플리케이션 로그
```

---

## 🔑 인증 시스템

### 기본 계정

```
Username: admin
Password: admin1234
Role: admin
```

### 회원가입

```bash
# API 사용
curl -X POST http://localhost:9000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "LoginId": "user1",
    "UserName": "사용자1",
    "Password": "password123"
  }'
```

### 로그인 플로우

```
1. POST /api/v1/auth/token (username + password)
   → AccessToken 수신

2. GET /api/v1/auth/me (Authorization: Bearer {token})
   → 사용자 정보 확인

3. 토큰을 localStorage에 저장
   → 이후 모든 API 요청에 포함
```

---

## 📊 API 엔드포인트

### 인증 API

```bash
# 로그인
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded
Body: username=admin&password=admin1234

# 회원가입
POST /api/v1/auth/signup
Content-Type: application/json
Body: {"LoginId": "user1", "UserName": "사용자", "Password": "pass123"}

# 사용자 정보
GET /api/v1/auth/me
Authorization: Bearer {token}
```

### 볼륨 API

```bash
# 볼륨 목록 (일반 사용자)
GET /api/volumes?LoginId=user1
Authorization: Bearer {token}

# 볼륨 목록 (관리자)
GET /api/admin/volumes
Authorization: Bearer {token}

# 볼륨 삭제 (관리자)
DELETE /api/admin/volumes/{volume_name}
Authorization: Bearer {token}

# 상세 정보
GET /api/raw-uploads?calculate_size=false
Authorization: Bearer {token}
```

### 업로드 API

```bash
# 이미지 업로드 및 변환 (관리자 전용)
POST /api/v1/upload
Authorization: Bearer {token}
Content-Type: multipart/form-data
Body: file=@image.tif

# 응답
{
  "message": "File uploaded and converted successfully: 20251208_143022_image",
  "volume_name": "20251208_143022_image",
  "size_mb": 585.23,
  "chunks_created": 256,
  "location": "tmp"
}
```

### 로그 API

```bash
# 내 로그 조회
GET /api/v1/image-logs/me?skip=0&limit=100&start_date=2025-12-01&end_date=2025-12-08
Authorization: Bearer {token}

# 로그 파일 목록
GET /api/logs/files
```

### 메모리 API

```bash
# 메모리 상태
GET /api/v1/memory-status

# 메모리 정리 (관리자)
POST /api/v1/memory-clean
Authorization: Bearer {token}
```

### Neuroglancer API

```bash
# Neuroglancer 상태 생성
GET /api/neuroglancer/state?volume_name=brain&location=converter
Authorization: Bearer {token}

# Precomputed 파일 서빙
GET /precomp/{volume_name}/{file_path}
```

---

## 👨‍💼 관리자 기능

### 이미지 업로드 & 변환

1. 관리자로 로그인 (`admin` / `admin1234`)
2. 상단 Admin 페이지 이동
3. "이미지 업로드" 섹션에서 파일 선택
4. "업로드 및 청크 변환" 버튼 클릭
5. 자동으로 Precomputed 형식으로 변환
6. "변환된 볼륨 목록"에서 확인

**지원 형식**: `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`, `.bmp`

**변환 과정**:
```
1. 원본 파일 업로드 → /mnt/tmp_uploads/TIMESTAMP_filename.tif
2. Precomputed 변환 → /mnt/tmp_uploads/TIMESTAMP_filename/
   ├── info (메타데이터)
   ├── provenance
   └── 0/ (청크 데이터)
       ├── 0-512_0-512_0-1
       ├── 512-1024_0-512_0-1
       └── ...
3. 원본 파일 삭제 (선택적)
```

### 볼륨 삭제

1. 관리자 페이지에서 "변환된 볼륨 목록" 확인
2. 삭제할 볼륨의 "🗑️ 삭제" 버튼 클릭
3. 확인 후 백그라운드로 삭제 진행

### 메모리 모니터링

실시간으로 다음 정보 확인:
- 서버 메모리 사용량
- 디스크 사용량
- 프로세스 메모리

---

## 📋 로깅 시스템

### 로그 형식

```json
{
  "timestamp": "2025-12-08T22:07:52.091538",
  "level": "INFO",
  "service": "viewer",
  "action": "view_image",
  "path": "/precomputed/converter/ROI_Mono_585MB/0/0-512_0-512_0-1",
  "method": "GET",
  "status": 200,
  "duration": 0.0105,
  "user": "test1",
  "user_id": "test1",
  "LoginId": "test1",
  "login_id": "test1"
}
```

### 로그 확인

**웹 UI**:
1. 로그인 후 "로그 히스토리" 페이지 접속
2. 기간/레벨 필터 선택
3. 자신의 활동 로그만 표시

**파일 시스템**:
```bash
# 호스트에서 확인
cat E:\GithubRepository\Projects\ati_lab_2025\viewer\logs\2025\12\08.txt

# Docker 컨테이너에서 확인
docker exec -it ati-viewer-backend cat /logs/2025/12/08.txt
```

---

## 🎯 사용 시나리오

### 시나리오 1: 연구자가 뇌 영상 분석

```
1. 로그인 (user1 / password123)
2. 메인 페이지에서 "converter" 위치 선택
3. "brain_scan" 데이터셋 클릭
4. Neuroglancer에서 3D 시각화
5. 관심 영역 발견 → 북마크 추가
6. 나중에 북마크 페이지에서 빠르게 재접근
```

### 시나리오 2: 관리자가 새 데이터 추가

```
1. 관리자 로그인 (admin / admin1234)
2. Admin 페이지 이동
3. "이미지 업로드" 섹션에서 TIFF 파일 선택
4. 자동 변환 대기 (대용량: 수 분 소요)
5. "변환된 볼륨 목록"에서 확인
6. 연구자에게 데이터 사용 가능 알림
```

### 시나리오 3: 로그 분석

```
1. 관리자 로그인
2. "로그 히스토리" 페이지 접속
3. 기간 선택 (최근 7일)
4. 사용자별 활동 확인
5. 에러 로그 필터링 (level=ERROR)
6. 문제 원인 파악
```

---

## 🔧 문제 해결

### 1. 로그인 실패

```bash
# 사용자 데이터 확인
cat data/users.json

# 기본 관리자 계정 재생성
docker-compose restart backend
# startup 이벤트에서 자동 생성됨
```

### 2. 파일 업로드 실패

```bash
# 업로드 디렉터리 권한 확인
ls -la /mnt/tmp_uploads

# 컨테이너 로그 확인
docker-compose logs -f backend

# 일반적인 원인:
# - 파일 크기 제한 (기본: 무제한)
# - 디스크 공간 부족
# - 파일 형식 불일치
```

### 3. 로그가 표시되지 않음

```bash
# 로그 파일 확인
ls -la logs/2025/12/

# 로그 내용 확인
cat logs/2025/12/08.txt | grep "user_id"

# 사용자 필드가 없으면 최신 코드로 업데이트
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 4. 볼륨이 표시되지 않음

```bash
# 볼륨 마운트 확인
docker-compose config

# 디렉터리 존재 확인
ls -la /mnt/converter_uploads
ls -la /mnt/f_uploads
ls -la /mnt/tmp_uploads

# info 파일 확인
cat /mnt/converter_uploads/*/info
```

### 5. Neuroglancer 로딩 실패

- 브라우저 콘솔 확인 (F12)
- CORS 에러 → docker-compose.yml 확인
- 파일 경로 에러 → 볼륨 마운트 확인
- 렌더링 에러 → info 파일 형식 확인

---

## 🛡️ 보안 고려사항

### JWT Secret Key

프로덕션 환경에서는 반드시 변경:

```yaml
# docker-compose.yml
environment:
  - JWT_SECRET_KEY=your-super-secret-key-here-at-least-32-characters-long
```

### 비밀번호 정책

- 최소 6자 이상
- bcrypt로 해시 저장
- 평문 비밀번호 로그 금지

### 파일 업로드 제한

```python
# main.py에서 설정
allowed_extensions = [".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"]
```

### 관리자 권한

- 볼륨 삭제: 관리자 전용
- 파일 업로드: 관리자 전용
- 메모리 정리: 관리자 전용

---

## 📈 성능 최적화

### 메모리 효율

- **스트리밍 처리**: 대용량 파일도 1-2GB 메모리로 처리
- **청크 기반 변환**: 512x512 청크로 분할
- **비동기 I/O**: aiofiles 사용

### 로그 최적화

- **JSON 라인 형식**: 한 줄에 하나의 로그
- **날짜별 분리**: 파일 크기 관리
- **인덱싱 불필요**: 전체 스캔으로 충분히 빠름

### Neuroglancer 최적화

- **Precomputed 형식**: 브라우저 최적화
- **다중 해상도**: 피라미드 스케일
- **Static 파일 서빙**: FastAPI StaticFiles

---

## 🔄 백업 및 복구

### 백업 대상

```bash
# 1. 사용자 데이터
cp data/users.json backup/users_$(date +%Y%m%d).json

# 2. 북마크 데이터
cp data/bookmarks.json backup/bookmarks_$(date +%Y%m%d).json

# 3. 로그 (선택적)
tar -czf backup/logs_$(date +%Y%m%d).tar.gz logs/
```

### 복구

```bash
# 사용자 데이터 복구
cp backup/users_20251208.json data/users.json

# 컨테이너 재시작
docker-compose restart backend
```

---

## 📝 개발 가이드

### 코드 구조

```python
# main.py 주요 섹션
1. Import 및 설정
2. FastAPI 앱 생성
3. JSON 파일 관리 (users, bookmarks)
4. 인증 함수 (JWT, bcrypt)
5. 로깅 미들웨어
6. API 엔드포인트
   - 인증 (/api/v1/auth/*)
   - 볼륨 (/api/volumes, /api/admin/volumes)
   - 업로드 (/api/v1/upload)
   - 로그 (/api/v1/image-logs/me)
   - Neuroglancer (/api/neuroglancer/*)
7. Static 파일 마운트
8. 시작 이벤트
```

### 새 API 추가

```python
@app.get("/api/v1/my-endpoint")
def my_endpoint(current_user: Dict = Depends(get_current_user_from_token)):
    """새로운 API 엔드포인트"""
    logger.info(f"User {current_user['LoginId']} called my_endpoint")
    return {"message": "Hello"}
```

### 로깅 추가

```python
from shared_logging import set_current_user, get_logger

logger = get_logger("viewer", "/logs")

# 사용자 컨텍스트 설정 후
logger.info({"action": "custom_action", "details": "..."})
```

---

## 🚧 알려진 제한사항

1. **단일 사용자 세션**: 동시 로그인 제한 없음 (JWT 기반)
2. **파일 크기**: 90GB 파일 처리 가능하나 변환 시간 소요
3. **3D 데이터**: Z축 1개 슬라이스만 지원 (2D 데이터)
4. **브라우저**: Chrome/Edge 권장 (Firefox: 일부 렌더링 이슈)

---

## 📞 지원

문제 발생 시:
1. 로그 확인: `docker-compose logs -f backend`
2. GitHub Issue 생성
3. 팀 내부 문의

---

## 📄 라이선스

ATI Lab 2025 Internal Project
