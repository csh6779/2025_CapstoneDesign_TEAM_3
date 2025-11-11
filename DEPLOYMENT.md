# 프론트엔드-백엔드 통합 가이드

## 📋 개요

이 문서는 React 프론트엔드와 FastAPI 백엔드를 통합하여 배포하는 방법을 설명합니다.

## 🏗️ 아키텍처

### 프로덕션 모드 (빌드 후 배포)
```
FastAPI 서버 (포트 8000)
├── API 엔드포인트 (/api/*, /v1/*)
├── 업로드 파일 (/uploads/*)
└── React 앱 (/, /login, /signup, etc.)
    └── static 파일 (/static/*)
```

### 개발 모드 (별도 서버)
```
React Dev Server (포트 3000)    FastAPI Server (포트 8000)
├── 핫 리로딩                     ├── API 엔드포인트
└── 프론트엔드 코드       ←CORS→  └── 업로드 파일
```

## 🚀 빠른 시작

### 1. 처음 설치하는 경우

#### Windows
```bash
# 1. 프론트엔드 빌드
build_frontend.bat

# 2. 서버 실행
start_server.bat
```

#### Linux/Mac
```bash
# 1. 프론트엔드 빌드
cd static
npm install
npm run build
cd ..

# 2. 서버 실행
uvicorn app.Services.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 접속 확인

- 메인 페이지: http://localhost:8000
- API 문서: http://localhost:8000/docs
- 볼륨 목록: http://localhost:8000/api/volumes/list

## 📂 디렉터리 구조

```
2025_CapstoneDesign_TEAM_3/
├── app/
│   └── Services/
│       └── main.py                    # FastAPI 앱 (수정됨)
├── static/
│   ├── src/                           # React 소스 코드
│   │   ├── pages/                     # 페이지 컴포넌트
│   │   ├── index.js                   # React 진입점
│   │   └── index.css                  # Tailwind CSS
│   ├── public/
│   │   └── index.html                 # HTML 템플릿
│   ├── package.json                   # npm 설정
│   ├── tailwind.config.js             # Tailwind 설정
│   └── build/                         # 빌드 결과물 (자동 생성)
│       ├── index.html
│       └── static/
│           ├── css/
│           └── js/
├── build_frontend.bat                 # 빌드 스크립트 (신규)
└── start_server.bat                   # 서버 실행 스크립트
```

## 🔧 main.py 변경 사항

### 변경 전
```python
# 정적 파일 마운트
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 루트 경로에서 index.html 제공
@app.get("/")
def read_root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
```

### 변경 후
```python
# 빌드 결과물 경로 추가
STATIC_DIR = BASE_DIR / "static"
BUILD_DIR = STATIC_DIR / "build"  # React 빌드 결과물

# React 빌드 결과물의 static 폴더만 마운트
if (BUILD_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BUILD_DIR / "static")), name="static")
else:
    logger.warning("React 빌드 결과물이 없습니다.")

# React Router 지원: 모든 경로에서 index.html 제공
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    # API 경로 제외
    if full_path.startswith("api/") or full_path.startswith("v1/") or full_path.startswith("uploads/"):
        raise HTTPException(status_code=404)
    
    # 빌드된 index.html 제공
    index_path = BUILD_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    # 빌드 안 됐으면 안내
    return {"message": "빌드가 필요합니다", "instruction": "build_frontend.bat 실행"}
```

## 🎯 주요 개선 사항

### 1. React Router 지원
- SPA 라우팅을 위해 모든 경로에서 `index.html` 제공
- API 경로(`/api/*`, `/v1/*`, `/uploads/*`)는 제외

### 2. 빌드 확인
- 서버 시작 시 빌드 결과물 존재 여부 확인
- 없으면 경고 메시지 출력

### 3. 올바른 파일 서빙
- `static/build/static/*` → `/static/*`로 매핑
- React가 기대하는 경로와 정확히 일치

## 🔄 개발 워크플로우

### 시나리오 1: 프론트엔드만 수정
```bash
# 개발 모드 (추천)
cd static
npm start  # localhost:3000에서 핫 리로딩

# 또는 빌드 후 확인
npm run build
cd ..
# start_server.bat 실행
```

### 시나리오 2: 백엔드만 수정
```bash
# FastAPI는 자동 리로드 지원
start_server.bat  # --reload 옵션으로 실행됨
```

### 시나리오 3: 풀스택 개발
```bash
# 터미널 1
start_server.bat

# 터미널 2
cd static
npm start
```

## ⚠️ 주의사항

### 1. 빌드 필수
프로덕션 배포 전에는 반드시 빌드해야 합니다:
```bash
build_frontend.bat
```

### 2. API 경로 충돌 방지
프론트엔드 라우트와 API 경로가 겹치지 않도록 주의:
- ✅ 프론트엔드: `/`, `/login`, `/signup`, `/log-history`
- ✅ API: `/api/*`, `/v1/*`, `/uploads/*`

### 3. CORS 설정
개발 모드에서는 CORS가 허용되어 있습니다:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

프로덕션에서는 `allow_origins`를 실제 도메인으로 제한하세요.

### 4. 환경 변수
프론트엔드에서 API URL을 하드코딩하지 말고 환경에 따라 설정:
```javascript
// 개발
const API_URL = 'http://localhost:8000';

// 프로덕션
const API_URL = window.location.origin;
```

## 🐛 문제 해결

### 문제 1: "빌드 결과물 없음" 경고
**증상:**
```
⚠️ 빌드 결과물 없음 - 'cd static && npm run build' 실행 필요
```

**해결:**
```bash
build_frontend.bat
```

### 문제 2: 404 에러 (페이지를 찾을 수 없음)
**원인:** React Router 경로가 제대로 서빙되지 않음

**해결:** 
1. 빌드가 제대로 되었는지 확인
2. `static/build/index.html` 존재 확인
3. 서버 재시작

### 문제 3: CSS/JS 파일 로드 실패
**원인:** 정적 파일 경로 불일치

**확인:**
```bash
# static/build/static 폴더 확인
dir static\build\static
```

**해결:** 빌드를 다시 실행

### 문제 4: API 호출 실패 (CORS 에러)
**개발 모드에서만 발생**

**해결:**
1. 백엔드 서버가 실행 중인지 확인
2. CORS 설정 확인 (`main.py`)
3. 브라우저 콘솔에서 정확한 에러 확인

### 문제 5: "npm: command not found"
**원인:** Node.js/npm이 설치되지 않음

**해결:**
1. https://nodejs.org/ 에서 Node.js 설치
2. LTS 버전 권장
3. 설치 후 터미널 재시작

## 📊 성능 고려사항

### 빌드 최적화
```bash
# 프로덕션 빌드 (최적화됨)
npm run build

# 빌드 결과물 크기 확인
du -sh static/build
```

### 캐싱
브라우저 캐싱을 위해 빌드 파일에 해시가 자동으로 추가됩니다:
```
static/build/static/js/main.abc123.js
static/build/static/css/main.xyz789.css
```

### Gzip 압축
프로덕션 배포 시 Nginx나 Apache에서 Gzip 압축 활성화를 권장합니다.

## 🚀 프로덕션 배포

### 1. 빌드
```bash
build_frontend.bat
```

### 2. 환경 변수 설정
```env
DEBUG=False
JWT_SECRET_KEY=<강력한-비밀키>
```

### 3. CORS 설정 업데이트
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 실제 도메인
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. HTTPS 사용
Let's Encrypt로 SSL 인증서 발급 후 HTTPS 사용

### 5. 서버 실행
```bash
uvicorn app.Services.main:app --host 0.0.0.0 --port 8000 --workers 4
```

또는 Gunicorn 사용:
```bash
gunicorn app.Services.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## 📝 체크리스트

배포 전 확인사항:
- [ ] `build_frontend.bat` 실행 완료
- [ ] `static/build/index.html` 존재 확인
- [ ] 서버 실행 시 "✅ 빌드 결과물 발견" 메시지 확인
- [ ] http://localhost:8000 접속 확인
- [ ] 로그인/회원가입 기능 테스트
- [ ] API 엔드포인트 테스트 (http://localhost:8000/docs)
- [ ] 환경 변수 설정 확인
- [ ] CORS 설정 확인 (프로덕션)
- [ ] 데이터베이스 마이그레이션 완료

## 📚 추가 자료

- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [React Router 문서](https://reactrouter.com/)
- [Create React App 문서](https://create-react-app.dev/)
- [Tailwind CSS 문서](https://tailwindcss.com/)

## 🤝 도움이 필요하신가요?

문제가 발생하면 다음을 확인하세요:
1. 서버 로그 확인 (`logs/` 디렉터리)
2. 브라우저 개발자 도구 콘솔
3. API 문서에서 테스트 (http://localhost:8000/docs)
4. GitHub Issues에 문의
