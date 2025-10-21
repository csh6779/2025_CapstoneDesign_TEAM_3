# 설치 및 초기 설정 가이드

## 📋 사전 요구사항
- Python 3.10+
- MySQL 8.0+
- Git

## 🚀 설치 단계

### 1. 저장소 클론
```bash
git clone <repository-url>
cd 2025_CapstoneDesign_TEAM_3
```

### 2. 가상 환경 생성 및 활성화
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
`.env` 파일 생성:
```env
# 데이터베이스 설정
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=your_database_name

# JWT 설정
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 5. 데이터베이스 생성
```sql
CREATE DATABASE your_database_name CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 6. 서버 실행
```bash
python app/Services/main.py
```

**중요**: 서버 시작 시 자동으로 다음 작업이 수행됩니다:
- ✅ 데이터베이스 테이블 생성
- ✅ UserImage 컬럼 타입 자동 확인 및 변경 (MEDIUMTEXT)
- ✅ 필요한 디렉터리 자동 생성

첫 실행 시 콘솔에서 다음과 같은 메시지를 확인할 수 있습니다:
```
================================================================================
🔧 데이터베이스 초기화 시작
================================================================================
✅ 데이터베이스 연결 성공
✅ 테이블 생성/확인 완료
✅ UserImage 컬럼이 MEDIUMTEXT로 변경되었습니다.
================================================================================
✅ 데이터베이스 초기화 완료
================================================================================
```

서버가 `http://localhost:8000`에서 실행됩니다.

---

## 🎯 주요 특징

### 자동 데이터베이스 관리
- **수동 마이그레이션 불필요**: 서버 시작 시 자동으로 데이터베이스를 확인하고 필요한 변경사항을 적용합니다.
- **안전한 업데이트**: 기존 데이터를 보존하면서 스키마만 업데이트합니다.
- **멱등성**: 여러 번 실행해도 안전합니다.

### 프로필 사진 지원
- **MEDIUMTEXT**: 최대 16MB의 Base64 인코딩 이미지 저장
- **권장 크기**: 원본 이미지 10MB 이하
- **자동 처리**: 서버가 자동으로 최적의 데이터 타입으로 설정

---

## 🔧 문제 해결

### 데이터베이스 연결 실패
`.env` 파일의 데이터베이스 설정을 확인하세요.

### 패키지 설치 오류
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### 데이터베이스 초기화 실패
서버 로그를 확인하고, 데이터베이스 사용자 권한을 확인하세요:
```sql
GRANT ALL PRIVILEGES ON your_database_name.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

---

## 📚 API 문서
서버 실행 후: `http://localhost:8000/docs`

## 🗂️ 프로젝트 구조
```
2025_CapstoneDesign_TEAM_3/
├── app/
│   ├── Services/
│   │   └── main.py          # 서버 진입점 (자동 DB 초기화 포함)
│   ├── database/
│   │   ├── database.py      # DB 연결
│   │   └── init_db.py       # 자동 초기화 스크립트 ⭐
│   ├── core/
│   │   ├── UserModel.py     # User 모델 (MEDIUMTEXT 타입)
│   │   └── ImageLogModel.py
│   ├── api/
│   └── utils/
├── static/                   # 프론트엔드
├── logs/                     # 자동 생성됨
├── uploads/                  # 자동 생성됨
└── .env                      # 환경 변수 (직접 생성)
```

---

## ✨ 빠른 시작
```bash
# 1. 클론 및 이동
git clone <repository-url>
cd 2025_CapstoneDesign_TEAM_3

# 2. 가상환경 및 패키지
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. .env 파일 생성 (데이터베이스 정보 입력)

# 4. MySQL 데이터베이스 생성
# mysql> CREATE DATABASE your_db_name;

# 5. 서버 실행 (자동으로 모든 초기화 수행)
python app/Services/main.py
```

끝! 🎉
