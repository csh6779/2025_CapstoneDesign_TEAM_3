# ATI Lab 2025 - Neuroglancer 통합 시스템

대용량 뇌 영상 데이터 처리 및 시각화를 위한 통합 시스템입니다.

## 시스템 구성

```
┌─────────────────────────────────────────────────────────┐
│                    ATI Lab 2025 System                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Converter (로컬)                                    │
│     - 대용량 이미지 → Precomputed 형식                    │
│     - 메모리 효율적 스트리밍 처리                          │
│     - F:/uploads, ./converter/uploads 지원               │
│                                                          │
│  2. Downloader (Docker)                                  │
│     - 양방향 전송: Docker ↔ F Drive ↔ Project             │
│     - 웹 인터페이스 기반 파일 관리                         │
│     - 전송 기록 자동 저장                                 │
│                                                          │
│  3. Viewer (Docker)                                      │
│     - 세 위치 통합 데이터셋 표시                           │
│     - Neuroglancer 기반 3D 시각화                         │
│     - 북마크 기능 (x, y, z 좌표 저장)                      │
│     - 토글 가능한 사이드바                                 │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## 빠른 시작

### 1️⃣ Converter (로컬 실행)

```bash
cd converter
python precomputed_writer.py
```

- F:/uploads 또는 ./converter/uploads에 이미지 배치
- CLI 메뉴에서 변환 실행
- Precomputed 형식으로 출력

### 2️⃣ Downloader (Docker)

```bash
cd downloader
./start.bat
# 또는: docker-compose up -d
```

- 웹: http://localhost:8001
- Docker ↔ F Drive ↔ Project 파일 전송
- 드래그 앤 드롭 방식

### 3️⃣ Viewer (Docker)

```bash
cd viewer
start.bat
# 또는(추천) : docker-compose up -d --build
# 도커 빌드한 경우 neuroglancer를 따로 빌드파일 만들 필요X
```

- 웹: http://localhost:3000
- 세 위치의 데이터셋 통합 표시
- 북마크로 특정 좌표 저장(보류)

## 전체 워크플로우

### 시나리오 A: 로컬 변환 → 즉시 확인

```bash
1. [로컬] Converter 실행
   └─> F:/uploads/brain.tif 선택
   └─> F Drive 출력 선택
   └─> F:/uploads/precomputed/brain 생성

2. [웹] Viewer 접속 (http://localhost:9000)
   └─> F Drive 섹션에서 'brain' 클릭
   └─> Neuroglancer에서 즉시 시각화
```

### 시나리오 B: 변환 → 전송 → 공유

```bash
1. [로컬] Converter로 변환
   └─> F:/uploads/sample.tif
   └─> F:/uploads/precomputed/sample

2. [웹] Downloader로 전송 (http://localhost:8001)
   └─> F Drive → Docker 전송
   └─> /tmp/uploads/sample로 복사

3. [웹] Viewer에서 확인 (http://localhost:9000)
   └─> Docker 섹션에서 'sample' 클릭
   └─> 팀원들과 URL 공유
```

### 시나리오 C: 북마크 활용

```bash
1. [웹] Viewer에서 데이터셋 열기
2. 관심 영역 탐색 (마우스 드래그)
3. 'Bookmarks' 탭 → '현재 위치 북마크 추가'
4. 이름: "종양 의심 영역", 설명: "추가 분석 필요"
5. 나중에 북마크 클릭으로 빠른 재방문
```

## 디렉터리 구조

```
E:\GithubRepository\Projects\ati_lab_2025\
│
├── converter/                      # 로컬 변환기
│   ├── backend/                    # 변환 로직
│   ├── uploads/                    # 프로젝트 업로드 폴더
│   ├── local_converter.py          # 메인 CLI 프로그램
│   ├── run_local_converter.bat     # 실행 스크립트
│   └── conversion_history.json     # 변환 기록
│
├── downloader/                     # Docker 전송 서비스
│   ├── backend/                    # FastAPI 서버
│   ├── frontend/                   # 웹 UI
│   ├── docker-compose.yml
│   ├── start.bat
│   └── transfer_history.json       # 전송 기록
│
├── viewer/                         # Docker 뷰어 서비스
│   ├── backend/                    # FastAPI 서버
│   ├── frontend/                   # 통합 뷰어 UI
│   ├── docker-compose.yml
│   ├── start.bat
│   └── bookmarks.json              # 북마크 저장
│
└── README.md                       # 이 파일
```

## 외부 저장소

```
F:\uploads\                         # F 드라이브
├── brain.tif                       # 원본 이미지
├── sample.bmp
└── precomputed/                    # 변환된 데이터
    ├── brain/
    │   ├── info
    │   └── 0/
    │       └── 0-512_0-512_0-1
    └── sample/
```

## 포트 구성

| 서비스 | 포트 | URL |
|--------|------|-----|
| Downloader | 8001 | http://localhost:8001 |
| Viewer | 9000 | http://localhost:9000 |

## 시스템 요구사항

### Converter (로컬)
- Python 3.9+
- RAM: 8GB 이상 권장
- 디스크: 변환할 파일 크기의 2배 이상

### Downloader & Viewer (Docker)
- Docker Desktop
- RAM: 4GB 이상
- 디스크: 10GB 이상

## 설치 및 설정

### 1. Python 환경 설정 (Converter용)

```bash
cd converter/backend
pip install -r requirements.txt
```

### 2. Docker 네트워크 생성

```bash
docker network create neuroglancer-network
```

### 3. 디렉터리 생성

```bash
# Windows
mkdir F:\uploads
mkdir F:\uploads\precomputed

# Linux/Mac
mkdir -p ~/uploads
mkdir -p ~/uploads/precomputed
```

## 문제 해결

### Converter: 메모리 부족

```bash
# 청크 크기 조절 (기본 512)
python local_converter.py
# 변환 시 512 입력 (더 작게 하면 느려짐)
```

### Downloader: 볼륨 마운트 에러

```bash
# F:/uploads 폴더 권한 확인
# Docker Desktop → Settings → Resources → File Sharing
# F:\ 드라이브 추가
```

### Viewer: 데이터셋이 표시되지 않음

```bash
# 1. 파일 구조 확인
ls F:/uploads/precomputed/brain/
# info 파일과 0/ 폴더가 있어야 함

# 2. 컨테이너 재시작
cd viewer
docker-compose restart
```

### 전체 시스템 재시작

```bash
# 모든 서비스 중지
cd downloader && docker-compose down
cd ../viewer && docker-compose down

# 모든 서비스 재시작
cd ../downloader && docker-compose up -d
cd ../viewer && docker-compose up -d
```

## 주요 기능

### ✅ Converter
- 대용량 파일 스트리밍 처리 (90GB+)
- 메모리 효율적 (8GB RAM으로 충분)
- 두 위치 지원 (F Drive, Project)
- 변환 기록 자동 저장

### ✅ Downloader
- 양방향 전송 (업로드/다운로드)
- 웹 인터페이스
- 실시간 파일 목록
- 전송 기록 추적

### ✅ Viewer
- 세 위치 통합 표시
- 토글 사이드바 (Claude 스타일)
- 북마크 기능 (좌표 저장)
- 실시간 위치 표시
- Neuroglancer WebGL 렌더링

## 성능

- **Converter**: 4GB TIFF → 약 2분 (512px 청크)
- **Downloader**: 1GB 전송 → 약 10초
- **Viewer**: 로딩 → 1초 이내

## 라이선스

ATI Lab 2025 Internal Use

## 기여자

- 한시원 (시스템 설계 및 구현)

## 버전

- v1.0.0 (2025-01-15)
  - 초기 통합 시스템 구축
  - 세 컴포넌트 완성
  - 북마크 기능 추가

## 지원

문제가 발생하면 다음을 확인하세요:

1. Docker Desktop 실행 중인지 확인
2. 포트 8001, 9000 사용 가능한지 확인
3. F:/uploads 폴더 접근 권한 확인
4. 로그 확인: `docker-compose logs -f [service]`

## 다음 단계

- [ ] 다중 사용자 지원
- [ ] 클라우드 스토리지 연동
- [ ] 실시간 협업 기능
- [ ] 자동 백업 시스템
- [ ] 성능 모니터링 대시보드
