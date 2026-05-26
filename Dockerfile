FROM python:3.11-slim

# 캐시 무효화용 (변경 시 재빌드 강제)
ARG CACHE_DATE=2026-05-26b

# Node.js 20 설치
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 프론트엔드 의존성 설치 및 빌드
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci

COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# Python 의존성 설치
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# 백엔드 코드 복사
COPY backend/ ./backend/

EXPOSE 8080

CMD ["sh", "-c", "cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
