# Bidirectional Transfer Service

Docker 서버와 로컬 저장소 간 양방향 파일 전송 서비스입니다.

## 특징

- ✅ **양방향 전송**: Docker ↔ F Drive ↔ Project
- ✅ **웹 인터페이스**: 직관적인 드래그 앤 드롭 방식
- ✅ **자동 동기화**: 파일 목록 실시간 업데이트
- ✅ **전송 기록**: 모든 전송 작업 자동 기록
- ✅ **대용량 지원**: 디렉터리 단위 전송 가능

## 사용 방법

### 1. Docker 컨테이너 실행

```bash
cd downloader
docker-compose up -d
```

### 2. 웹 인터페이스 접속

```
http://localhost:8001
```

### 3. 파일 전송

1. **출발지 선택**: Docker, F Drive, Project 중 하나의 파일 클릭
2. **목적지 선택**: 드롭다운에서 대상 위치 선택
3. **전송 시작**: 전송 버튼 클릭

## API 엔드포인트

### 파일 목록 조회

```bash
# 모든 위치의 파일 목록
GET /api/files

# 특정 위치의 파일 목록
GET /api/files/{location}
# location: docker, f_drive, project
```

### 파일 전송

```bash
POST /api/transfer
Content-Type: application/json

{
  "source_location": "docker",
  "target_location": "f_drive",
  "item_name": "brain_scan_precomputed",
  "overwrite": false
}
```

**응답 예시:**
```json
{
  "success": true,
  "item_name": "brain_scan_precomputed",
  "source_location": "docker",
  "target_location": "f_drive",
  "type": "directory",
  "size_mb": 1250.45,
  "duration_seconds": 15.32,
  "source_path": "/tmp/uploads/brain_scan_precomputed",
  "target_path": "/app/f_uploads/brain_scan_precomputed"
}
```

### 파일 다운로드

```bash
# 파일 또는 디렉터리를 ZIP으로 다운로드
GET /api/download/{location}/{item_name}
```

### 파일 업로드

```bash
POST /api/upload/{location}
Content-Type: multipart/form-data
```

### 전송 기록

```bash
# 최근 전송 기록 조회 (기본 20개)
GET /api/history?limit=20

# 전송 기록 초기화
DELETE /api/history
```

### 파일 삭제

```bash
DELETE /api/files/{location}/{item_name}
```

## 디렉터리 구조

```
/tmp/uploads              # Docker 서버 내부 (컨테이너)
F:/uploads                # F Drive (호스트)
./converter/uploads       # 프로젝트 폴더 (호스트)
```

## 전송 시나리오

### 시나리오 1: Converter → Viewer
1. Local Converter로 `F:/uploads/brain.tif` 변환
2. 출력: `F:/uploads/precomputed/brain`
3. Downloader로 F Drive → Docker 전송
4. Viewer에서 Docker 위치의 파일 확인

### 시나리오 2: Docker → 로컬 백업
1. Docker에서 변환 완료된 파일
2. Downloader로 Docker → F Drive 전송
3. 로컬에 영구 보관

### 시나리오 3: 프로젝트 간 공유
1. Project 폴더에서 작업
2. Downloader로 Project → Docker 전송
3. 팀원들이 Docker에서 접근

## 장점 vs 로컬 실행 비교

### Docker 서버 사용 (현재 구현) ✅

**장점:**
- ✅ 통합 관리: docker-compose로 간편 실행
- ✅ 네트워크 통신: Viewer와 같은 네트워크에서 파일 공유
- ✅ 포트 노출: 웹 인터페이스로 어디서나 접근
- ✅ 자동 재시작: 컨테이너 crash 시 자동 복구
- ✅ 일관된 환경: Python 버전, 라이브러리 통일

**단점:**
- ⚠️ 볼륨 마운트 필요: F:/uploads를 컨테이너에 마운트
- ⚠️ 메모리 제한: 대용량 전송 시 컨테이너 메모리 제약

**권장 사용:**
- 일반적인 파일 전송 (< 10GB)
- 웹 인터페이스 필요
- 여러 서비스와 연동

### 로컬 실행 (대안)

**장점:**
- ✅ 메모리 제약 없음: 호스트 RAM 전체 활용
- ✅ 직접 접근: 볼륨 마운트 없이 직접 파일 접근
- ✅ 빠른 전송: 컨테이너 오버헤드 없음

**단점:**
- ❌ Python 환경 필요: 별도 설치 필요
- ❌ 수동 실행: 매번 스크립트 실행 필요
- ❌ 네트워크 격리: Viewer와 통신 불가

**권장 사용:**
- 초대용량 파일 (> 10GB)
- CLI만 필요
- 네트워크 통신 불필요

## 문제 해결

### 볼륨 마운트 에러
```bash
# Windows: F:/uploads 폴더 권한 확인
# 폴더가 없으면 생성
mkdir F:\uploads
```

### 전송 실패
- 대상 위치에 충분한 공간이 있는지 확인
- 덮어쓰기 옵션 체크 (기존 파일 존재 시)

### 컨테이너 재시작
```bash
docker-compose restart
```

### 로그 확인
```bash
docker-compose logs -f downloader
```

## 다음 단계

전송된 파일은 Viewer에서 확인할 수 있습니다.
- Viewer는 세 위치의 파일을 모두 통합하여 표시
- 북마크 기능으로 특정 좌표 저장 가능
