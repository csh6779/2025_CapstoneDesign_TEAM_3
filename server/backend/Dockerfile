FROM python:3.10-slim-bookworm

# 작업 디렉터리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필수 도구 설치
# 네트워크 오류 대비 재시도 로직 추가
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing \
    gcc \
    g++ \
    make \
    libjpeg62-turbo \
    libjpeg62-turbo-dev \
    libpng16-16 \
    libpng-dev \
    zlib1g \
    zlib1g-dev \
    pkg-config \
    procps \
    || (apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    gcc \
    g++ \
    make \
    libjpeg62-turbo \
    libjpeg62-turbo-dev \
    libpng16-16 \
    libpng-dev \
    zlib1g \
    zlib1g-dev \
    pkg-config \
    procps) && \
    rm -rf /var/lib/apt/lists/*

# requirements.txt 먼저 복사 (캐시 활용)
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 데이터 디렉터리 생성
RUN mkdir -p /app/data/precomputed && \
    mkdir -p /app/data/precomputed/temp

# 환경 변수 설정
ENV DATA_DIR=/app/data/precomputed \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 포트 노출
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/memory-status', timeout=5)" || exit 1

# 애플리케이션 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
