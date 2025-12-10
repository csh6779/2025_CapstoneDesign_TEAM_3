FROM python:3.11-slim

WORKDIR /viewer

# 시스템 의존성 설치 (MySQL 클라이언트 제거, dos2unix 추가)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY ./app /viewer
COPY ./backend /viewer/backend

# 데이터 디렉터리 생성
RUN mkdir -p /viewer/data

# Entrypoint 복사 및 변환
COPY entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 9000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000", "--reload"]
