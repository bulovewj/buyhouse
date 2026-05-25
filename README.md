# 🏠 부산 내집마련 대시보드

부산 거주자를 위한 개인용 부동산 정보 허브.  
청약·공고 자동 수집, 실거래가 조회, 시세 분석, 뉴스 AI 요약, 카카오톡·이메일 알림을 하나의 대시보드에서 제공합니다.

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 청약·공고 수집 | 청약·줍줍·행복주택·공공임대 자동 수집, D-day 표시 |
| 실거래가 조회 | 부산 전 구 아파트·빌라 실거래가 (국토부 API) |
| 시세 분석 | 구별 평균가·전세가율·거래량·미분양 차트 |
| 뉴스 AI 요약 | 네이버 뉴스·블로그 수집 + Claude AI 요약·감성분석 |
| 카카오톡 알림 | 신규 공고 감지 시 즉시 카톡(나에게 보내기) 알림 |
| 이메일 알림 | Gmail SMTP 선택적 수신 |
| 대출계산기 | LTV·DSR·스트레스 DSR 기반 대출 가능 여부 계산 |

---

## 기술 스택

```
Backend   Python 3.11+ / FastAPI / SQLAlchemy 2.0 (async) / APScheduler / SQLite
Frontend  React 18 / Vite / Tailwind CSS / Recharts / Axios
AI        Claude API (claude-haiku-4-5)
배포      Railway
```

---

## 로컬 개발 환경 설정

### 1. 저장소 클론

```bash
git clone <repo-url>
cd buy_house_project
```

### 2. 환경변수 설정

```bash
cp .env.example .env
```

`.env`를 열어 필요한 API 키를 입력합니다. API 키 없이 개발할 때는 `USE_MOCK=true`(기본값)로 두면 됩니다.

### 3. 백엔드 실행

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 개발 서버 시작 (포트 8000)
USE_MOCK=true uvicorn main:app --reload
```

### 4. 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev    # 포트 5173, /api → localhost:8000 프록시
```

브라우저에서 `http://localhost:5173` 접속.

---

## 환경변수 목록

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `USE_MOCK` | true 시 목업 데이터 사용 | `true` |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite+aiosqlite:///./dashboard.db` |
| `MOLIT_API_KEY` | 국토부 실거래가 API 키 | — |
| `APPLYHOME_API_KEY` | 청약홈 오픈 API 키 | — |
| `LH_API_KEY` | LH청약센터 API 키 | — |
| `NAVER_CLIENT_ID` | 네이버 검색 API Client ID | — |
| `NAVER_CLIENT_SECRET` | 네이버 검색 API Secret | — |
| `ANTHROPIC_API_KEY` | Claude API 키 | — |
| `KAKAO_ACCESS_TOKEN` | 카카오 액세스 토큰 | — |
| `GMAIL_USER` | Gmail 주소 | — |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 | — |
| `ADMIN_TOKEN` | 어드민 엔드포인트 인증 토큰 | `change-me` |
| `ALLOWED_ORIGINS` | CORS 허용 출처 (쉼표 구분) | `http://localhost:5173` |

> **보안 주의**: `ADMIN_TOKEN`은 반드시 강력한 랜덤 값으로 변경하세요.  
> 생성 방법: `openssl rand -hex 32`

---

## API 문서

서버 실행 후 `http://localhost:8000/docs` (Swagger UI)에서 전체 API를 확인할 수 있습니다.

### 주요 엔드포인트

```
GET  /api/subscriptions        청약·공고 목록 (type, page, limit)
GET  /api/transactions         실거래가 목록 (district, dong, page, limit)
GET  /api/news                 뉴스 목록 (sentiment, source_type, page, limit)
GET  /api/policy-news          정책 뉴스 목록
GET  /api/market-stats         구별 시세 통계
GET  /api/settings             앱 설정 조회
PUT  /api/settings             앱 설정 변경
POST /api/calculator/calculate 대출 가능 금액 계산
POST /api/notifications/test   알림 테스트 발송
POST /api/notifications/run-ai 뉴스 AI 분석 수동 실행
POST /api/admin/run-update     전체 데이터 수동 갱신 (X-Admin-Token 필요)
POST /api/admin/run-urgent     줍줍 긴급 체크 (X-Admin-Token 필요)
GET  /healthz                  헬스체크
```

---

## 통합 테스트

```bash
cd backend
source .venv/bin/activate

# 로컬 서버 대상
python3 test_integration.py

# 배포 서버 대상
python3 test_integration.py https://your-app.up.railway.app
```

---

## Railway 배포

### 1. Railway 프로젝트 생성

```bash
npm install -g @railway/cli
railway login
railway init
```

### 2. 환경변수 설정

Railway 대시보드 → Variables 탭에서 `.env.example`의 변수를 입력합니다.  
필수 설정:

```
USE_MOCK=false
DATABASE_URL=sqlite+aiosqlite:///./dashboard.db
ADMIN_TOKEN=<openssl rand -hex 32 결과>
ALLOWED_ORIGINS=https://your-app.up.railway.app
```

### 3. 배포

```bash
railway up
```

`railway.toml`의 설정에 따라:
1. 프론트엔드 빌드 (`npm ci && npm run build`) → `backend/static/`에 출력
2. Python 의존성 설치
3. `uvicorn main:app --host 0.0.0.0 --port $PORT` 실행

FastAPI가 `/api/*` 요청은 API로, 나머지는 React SPA(`index.html`)로 처리합니다.

### 4. 배포 후 확인

```bash
python3 backend/test_integration.py https://your-app.up.railway.app
```

---

## 데이터 갱신 주기

| 작업 | 주기 |
|------|------|
| 전체 데이터 (청약·실거래·뉴스·시세) | 매일 00:00 KST |
| 줍줍(무순위) 긴급 공고 체크 | 매 6시간 (0, 6, 12, 18시) |
| 뉴스 AI 분석 | 전체 갱신 직후 자동 실행 |

---

## 폴더 구조

```
buy_house_project/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 라우터
│   │   ├── services/     # 데이터 수집·AI·알림 서비스
│   │   ├── models/       # SQLAlchemy ORM 모델
│   │   ├── scheduler/    # APScheduler 작업
│   │   └── core/         # 설정·DB·목업 데이터
│   ├── main.py
│   ├── requirements.txt
│   └── test_integration.py
├── frontend/
│   └── src/
│       ├── pages/        # 8개 페이지 컴포넌트
│       ├── components/   # 공통 컴포넌트
│       └── hooks/        # useApi 훅
├── .env.example
├── railway.toml
└── README.md
```

---

## 라이선스

개인 프로젝트 — 상업적 이용 금지.
