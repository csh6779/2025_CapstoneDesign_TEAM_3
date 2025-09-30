FROM python:3.11-slim

# 런타임 라이브러리(압축/PNG 등) + 빌드 기본툴
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo libpng16-16 zlib1g gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py generate_volume.py ./ 
COPY static ./static

# 데이터 및 업로드 디렉터리
RUN mkdir -p /app/data/precomputed /app/uploads

EXPOSE 8000
