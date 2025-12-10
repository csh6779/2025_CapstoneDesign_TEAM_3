# ATI Lab 2025 - Viewer 설치 및 설정 가이드

완전한 설치부터 실행까지의 단계별 가이드입니다.

---

## 📋 목차

1. [시스템 요구사항](#시스템-요구사항)
2. [설치 과정](#설치-과정)
3. [초기 설정](#초기-설정)
4. [실행 및 확인](#실행-및-확인)
5. [문제 해결](#문제-해결)
6. [고급 설정](#고급-설정)

---

## 시스템 요구사항

### 필수 소프트웨어

- **OS**: Windows 10/11 (WSL2 필수)
- **Docker Desktop**: 최신 버전
- **RAM**: 8GB 이상 (16GB 권장)
- **디스크 공간**: 50GB 이상 여유 공간

### 포트 사용

- `9000`: Viewer 백엔드 & 프론트엔드
- `8080`: Neuroglancer (선택적)

### 디스크 구조

```
E:\GithubRepository\Projects\ati_lab_2025\
├── converter/              # Converter 서비스
│   └── uploads/            # 변환된 데이터
├── viewer/                 # Viewer 서비스 (현재)
│   ├── data/               # 사용자/북마크 JSON
│   └── logs/               # 애플리케이션 로그
└── F:\uploads\             # F 드라이브 데이터 저장소
```

---

## 설치 과정

### 1. Docker Desktop 설치 확인

```powershell
# Docker 버전 확인
docker --version
docker-compose --version

# WSL2 상태 확인
wsl --list --verbose
```

**출력 예시**:
```
Docker version 24.0.7, build afdd53b
Docker Compose version v2.23.3
  NAME                   STATE           VERSION
* docker-desktop         Running         2
```

### 2. F 드라이브 공유 설정

Docker Desktop에서 F 드라이브 접근 권한 설정:

1. Docker Desktop 실행
2. Settings → Resources → File Sharing
3. `F:\` 드라이브 추가
4. "Apply & Restart" 클릭

### 3. 프로젝트 디렉터리 이동

```powershell
cd E:\GithubRepository\Projects\ati_lab_2025\viewer
```

### 4. 환경 파일 확인

`.env` 파일이 있는지 확인 (없으면 생성):

```env
# JWT 설정
JWT_SECRET_KEY=ati-lab-2025-super-secret-key-change-in-production-please
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 볼륨 경로
CONVERTER_UPLOADS_DIR=/mnt/converter_uploads
F_UPLOADS_DIR=/mnt/f_uploads
TMP_UPLOADS_DIR=/mnt/tmp_uploads

# Neuroglancer
NEUROGLANCER_URL=http://localhost:8080
```

---

## 초기 설정

### 1. entrypoint.sh 라인 엔딩 수정

Windows에서 작성된 스크립트는 CRLF 라인 엔딩을 사용하므로 Unix 형식(LF)으로 변환:

```powershell
# PowerShell에서 실행
$file = "entrypoint.sh"
$text = [IO.File]::ReadAllText($file)
$text = $text -replace "`r`n", "`n"
[IO.File]::WriteAllText($file, $text)
```

**확인**:
```powershell
# 파일 내용 미리보기
Get-Content entrypoint.sh -Head 5
```

### 2. 필수 디렉터리 생성

```powershell
# 데이터 디렉터리 생성
New-Item -ItemType Directory -Force -Path ".\data"
New-Item -ItemType Directory -Force -Path ".\logs"

# 권한 확인
Get-Acl .\data
Get-Acl .\logs
```

### 3. Docker 이미지 빌드

```powershell
# 캐시 없이 클린 빌드
docker-compose build --no-cache

# 빌드 진행 상황 확인
# - Python 의존성 설치
# - dos2unix 설치
# - 애플리케이션 코드 복사
```

**예상 소요 시간**: 5-10분

---

## 실행 및 확인

### 1. 컨테이너 시작

```powershell
# 백그라운드에서 실행
docker-compose up -d

# 로그 실시간 확인
docker-compose logs -f backend
```

**정상 로그 예시**:
```
🔥🔥🔥 JSON-based Authentication - 기존 API 형식 유지 🔥🔥🔥
2025-12-08 22:00:00,000 - viewer - INFO - 🔬 ATI Lab 2025 - Neuroglancer Viewer v3.0.0
2025-12-08 22:00:00,000 - viewer - INFO - ✅ Available locations: ['converter', 'f_drive', 'tmp']
INFO:     Application startup complete.
```

### 2. 서비스 접속 확인

**웹 브라우저로 접속**:
```
http://localhost:9000
```

**로그인 테스트**:
- Username: `admin`
- Password: `admin1234`

### 3. API 상태 확인

```powershell
# PowerShell에서 실행
Invoke-WebRequest -Uri "http://localhost:9000/api/health" -UseBasicParsing
```

**정상 응답**:
```json
{
  "status": "healthy",
  "locations": ["converter", "f_drive", "tmp"]
}
```

### 4. 데이터 확인

```powershell
# 사용자 데이터 확인
Get-Content .\data\users.json

# 볼륨 마운트 확인
docker-compose exec backend ls -la /mnt/converter_uploads
docker-compose exec backend ls -la /mnt/f_uploads
docker-compose exec backend ls -la /mnt/tmp_uploads
```

---

## 문제 해결

### 문제 1: 컨테이너 시작 실패

**증상**:
```
ERROR: failed to create shim task: OCI runtime create failed
```

**해결**:
```powershell
# WSL 재시작
wsl --shutdown

# Docker Desktop 재시작
# Settings → Troubleshoot → Restart Docker Desktop

# 컨테이너 재시작
docker-compose down
docker-compose up -d
```

### 문제 2: entrypoint.sh 실행 오류

**증상**:
```
exec /entrypoint.sh: exec format error
```

**원인**: Windows CRLF 라인 엔딩

**해결**:
```powershell
# PowerShell에서 변환
$file = "entrypoint.sh"
$text = [IO.File]::ReadAllText($file)
$text = $text -replace "`r`n", "`n"
[IO.File]::WriteAllText($file, $text)

# 재빌드
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 문제 3: 볼륨 마운트 실패

**증상**:
```
Error response from daemon: invalid mount config for type "bind"
```

**해결**:
```powershell
# 경로 확인
Test-Path E:\GithubRepository\Projects\ati_lab_2025\converter\uploads
Test-Path F:\uploads

# Docker Desktop에서 F 드라이브 공유 확인
# Settings → Resources → File Sharing

# docker-compose.yml 경로 수정 (절대 경로 사용)
volumes:
  - E:/GithubRepository/Projects/ati_lab_2025/converter/uploads:/mnt/converter_uploads:ro
  - F:/uploads:/mnt/f_uploads:ro
```

### 문제 4: 포트 충돌

**증상**:
```
Error starting userland proxy: listen tcp 0.0.0.0:9000: bind: address already in use
```

**해결**:
```powershell
# 포트 사용 확인
netstat -ano | findstr :9000

# 프로세스 종료 (PID 확인 후)
Stop-Process -Id <PID> -Force

# 또는 docker-compose.yml에서 포트 변경
ports:
  - "9001:9000"  # 호스트 포트를 9001로 변경
```

### 문제 5: 로그인 실패

**증상**: "Invalid credentials"

**해결**:
```powershell
# 사용자 데이터 확인
docker-compose exec backend cat /viewer/data/users.json

# 없으면 컨테이너 재시작 (자동 생성)
docker-compose restart backend

# 로그 확인
docker-compose logs backend | Select-String "admin account"
```

### 문제 6: 이미지 업로드 실패

**증상**: 500 Internal Server Error

**해결**:
```powershell
# 업로드 디렉터리 권한 확인
docker-compose exec backend ls -la /mnt/tmp_uploads

# 디렉터리 생성
docker-compose exec backend mkdir -p /mnt/tmp_uploads

# requirements.txt 확인
docker-compose exec backend pip list | Select-String "tifffile|zarr|Pillow"

# 필요시 재설치
docker-compose exec backend pip install tifffile zarr Pillow
```

### 문제 7: 로그가 기록되지 않음

**증상**: `/logs` 디렉터리가 비어있음

**해결**:
```powershell
# 로그 디렉터리 확인
docker-compose exec backend ls -la /logs

# 권한 확인
docker-compose exec backend stat /logs

# shared_logging.py 확인
docker-compose exec backend cat /app/shared_logging.py | Select-String "get_logger"

# main.py에서 shared_logging 사용 확인
docker-compose exec backend cat /app/main.py | Select-String "shared_logging"
```

---

## 고급 설정

### 1. 개발 모드 (Hot Reload)

코드 변경 시 자동으로 서버 재시작:

```yaml
# docker-compose.yml 수정
services:
  backend:
    command: uvicorn main:app --host 0.0.0.0 --port 9000 --reload
    volumes:
      - ./app:/app:ro  # 코드 볼륨 마운트
```

**재시작**:
```powershell
docker-compose down
docker-compose up -d
```

### 2. 프로덕션 모드

**JWT Secret 변경**:
```powershell
# PowerShell에서 강력한 키 생성
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
```

**docker-compose.yml 수정**:
```yaml
environment:
  - JWT_SECRET_KEY=<생성된 키>
  - JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60  # 1시간으로 단축
```

### 3. 로그 레벨 조정

```python
# app/main.py 수정
logger = get_logger("viewer", "/logs")
logger.setLevel(logging.DEBUG)  # DEBUG, INFO, WARNING, ERROR
```

### 4. 메모리 제한

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

### 5. 백업 자동화

```powershell
# backup.ps1 스크립트 생성
$date = Get-Date -Format "yyyyMMdd_HHmmss"

# 사용자 데이터 백업
Copy-Item data\users.json "backup\users_$date.json"
Copy-Item data\bookmarks.json "backup\bookmarks_$date.json"

# 로그 압축
Compress-Archive -Path logs\* -DestinationPath "backup\logs_$date.zip"

Write-Host "Backup completed: $date"
```

**Task Scheduler 등록**:
```powershell
# 매일 새벽 2시 실행
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File E:\...\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName "ATI_Viewer_Backup" -Action $action -Trigger $trigger
```

---

## 확인 체크리스트

설치 완료 후 다음 항목들을 확인하세요:

- [ ] Docker 컨테이너 실행 중 (`docker-compose ps`)
- [ ] http://localhost:9000 접속 가능
- [ ] 로그인 성공 (`admin` / `admin1234`)
- [ ] 볼륨 목록 표시 (최소 1개 이상)
- [ ] 이미지 업로드 테스트 (관리자)
- [ ] 로그 조회 가능 (로그 히스토리 페이지)
- [ ] Neuroglancer 렌더링 정상
- [ ] 북마크 추가/삭제 정상

---

## 유지보수

### 일일 점검

```powershell
# 컨테이너 상태 확인
docker-compose ps

# 로그 확인 (에러만)
docker-compose logs --tail=100 backend | Select-String "ERROR"

# 디스크 사용량 확인
docker system df
```

### 주간 점검

```powershell
# 로그 파일 크기 확인
Get-ChildItem -Path logs -Recurse | Measure-Object -Property Length -Sum

# 사용자 수 확인
docker-compose exec backend cat /viewer/data/users.json | Select-String "LoginId"

# Docker 이미지 정리
docker image prune -a -f
```

### 월간 점검

```powershell
# 전체 백업
.\backup.ps1

# Docker Desktop 업데이트
# Windows Update 확인
# 디스크 공간 확인 (50GB 이상 유지)
```

---

## 제거

완전히 제거하려면:

```powershell
# 1. 컨테이너 중지 및 제거
docker-compose down -v

# 2. 이미지 제거
docker rmi ati_lab_2025_viewer_backend

# 3. 볼륨 제거 (선택적)
docker volume prune -f

# 4. 데이터 백업 후 디렉터리 제거
Remove-Item -Path data -Recurse
Remove-Item -Path logs -Recurse
```

---

## 다음 단계

설치가 완료되면:

1. [README.md](README.md) - 전체 기능 가이드
2. 관리자 페이지에서 테스트 이미지 업로드
3. 일반 사용자 계정 생성
4. 북마크 기능 테스트
5. 로그 시스템 확인

---

## 지원

문제가 지속되면:
1. `docker-compose logs -f backend > error_log.txt` 저장
2. GitHub Issue 생성
3. 팀 내부 문의

---

**마지막 업데이트**: 2025-12-08
**버전**: v3.0.0 (JSON-based Authentication)
