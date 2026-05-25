# CLAUDE.md — 부산 내집마련 대시보드

> 이 파일은 Claude Code가 프로젝트 전반을 이해하기 위한 문서입니다.
> 개발 시작 전 반드시 읽고 규칙을 준수하세요.

---

## 프로젝트 목적 및 주요 기능

### 목적
부산 거주 개인 사용자가 부동산 관련 정보를 한 곳에서 확인하고,
새로운 청약·공고 발생 시 즉시 알림을 받을 수 있는 **개인용 부동산 정보 허브**.

### 주요 기능

| 기능 | 설명 |
|------|------|
| 청약·공고 수집 | 청약, 줍줍(무순위), 행복주택, 공공임대 모집공고 자동 수집 |
| 실거래가 조회 | 부산 전 구 아파트·빌라 실거래가 (국토부 API) |
| 시세 분석 | 구별 평균가, 전세가율, 거래량, 미분양 현황 |
| 개발 호재·정책 뉴스 | 부산 재개발·재건축·정부 부동산 정책 뉴스 자동 수집 |
| SNS 반응 분석 | 네이버 뉴스·블로그 수집 + Claude AI 요약 + 긍/부정 감성분석 |
| 카카오톡 알림 | 신규 공고 감지 시 즉시 카톡 알림 (나에게 보내기) |
| 이메일 알림 | Gmail SMTP 기반 선택적 이메일 수신 |
| 알림 설정 | 항목별 ON/OFF, 수신 채널 선택 |

### 데이터 갱신 주기
- 전체 데이터: **매일 00:00 KST** 자동 갱신
- 줍줍(무순위) 긴급 공고: **매 6시간마다** 체크

---

## 기술 스택

### 백엔드
```
Python 3.11
FastAPI         — REST API 서버
SQLAlchemy      — ORM
SQLite          — 로컬 DB (배포 시 Supabase로 이전 가능)
APScheduler     — 자동 갱신 스케줄러
httpx           — 비동기 HTTP 클라이언트
Anthropic SDK   — Claude API (요약·감성분석)
```

### 프론트엔드
```
React 18
Tailwind CSS    — 스타일링
React Router    — 페이지 라우팅
Recharts        — 차트 (시세 분석)
Axios           — API 통신
```

### 외부 API
```
국토부 실거래가 공공API     — 실거래가
청약홈 오픈API              — 청약·줍줍 공고
LH청약센터 API              — 행복주택·공공임대
네이버 검색 API (뉴스·블로그) — SNS 반응 수집
카카오 나에게 보내기 API    — 카톡 알림
Gmail SMTP                  — 이메일 알림
Claude API (Anthropic)      — 요약·감성분석
```

### 배포
```
Railway (백엔드 + 프론트 정적 서빙)
```

---

## 폴더 구조

```
buy_house_project/
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI 라우터
│   │   │   ├── subscriptions.py  # 청약·공고 API
│   │   │   ├── transactions.py   # 실거래가 API
│   │   │   ├── news.py           # 뉴스·반응 API
│   │   │   ├── market.py         # 시세 분석 API
│   │   │   ├── notifications.py  # 알림 발송 API
│   │   │   └── settings.py       # 설정 API
│   │   ├── services/             # 데이터 수집 서비스
│   │   │   ├── subscription_service.py
│   │   │   ├── transaction_service.py
│   │   │   ├── news_service.py
│   │   │   ├── market_stats_service.py
│   │   │   ├── ai_service.py     # Claude API 연동
│   │   │   └── notification_service.py
│   │   ├── models/               # SQLAlchemy ORM 모델
│   │   │   └── models.py
│   │   ├── scheduler/            # APScheduler 작업
│   │   │   └── tasks.py
│   │   └── core/                 # 공통 설정
│   │       ├── config.py         # 환경변수 로드
│   │       └── database.py       # DB 연결
│   ├── main.py                   # 앱 진입점
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/           # 공통 컴포넌트
│   │   │   ├── Navbar.jsx
│   │   │   ├── BottomTab.jsx     # 모바일 하단 탭
│   │   │   ├── Card.jsx
│   │   │   └── Badge.jsx
│   │   ├── pages/                # 페이지 컴포넌트
│   │   │   ├── Dashboard.jsx     # 홈 대시보드
│   │   │   ├── Subscriptions.jsx
│   │   │   ├── Transactions.jsx
│   │   │   ├── Market.jsx
│   │   │   ├── News.jsx
│   │   │   ├── Policy.jsx
│   │   │   └── Settings.jsx
│   │   ├── hooks/                # 커스텀 훅
│   │   │   └── useApi.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── .env                          # 환경변수 (git 제외)
├── .env.example                  # 환경변수 예시 (git 포함)
├── .gitignore
├── CLAUDE.md                     # 이 파일
└── README.md
```

---

## 개발 규칙 및 주의사항

### 필수 규칙

**1. 환경변수는 반드시 .env에서 불러올 것**
```python
# ✅ 올바른 방법
from app.core.config import settings
api_key = settings.ANTHROPIC_API_KEY

# ❌ 절대 금지
api_key = "sk-ant-xxxx"  # 하드코딩 금지
```

**2. 모든 외부 API 호출은 try/except로 감쌀 것**
```python
# ✅ 올바른 방법 — 구체적 예외 타입 우선 처리
import httpx

try:
    result = await fetch_subscription_data()
except httpx.HTTPStatusError as e:
    logger.error(f"청약 HTTP 오류 {e.response.status_code}: {e}")
    return []
except httpx.TimeoutException as e:
    logger.error(f"청약 요청 타임아웃: {e}")
    return []
except Exception as e:
    logger.error(f"청약 데이터 수집 실패: {e}")
    return []  # 빈 값 반환, 앱 중단 금지
```

**3. 비동기(async/await) 일관성 유지**
- 모든 서비스 함수는 `async def`로 작성
- DB 작업도 비동기 세션 사용 (`AsyncSession`)
- `scheduler/tasks.py`에서 줍줍 긴급 공고 체크는 반드시 **6시간 주기 (cron: `0 */6 * * *`)** 로 등록할 것

**4. 한국어 주석 사용**
```python
# ✅ 올바른 방법
# 부산 지역 데이터만 필터링 (시도코드: 26)
filtered = [item for item in data if item["sido"] == "부산"]
```

**5. 타임존 고정**
```python
from zoneinfo import ZoneInfo
KST = ZoneInfo("Asia/Seoul")
now = datetime.now(KST)  # 항상 KST 사용
```

**6. 어드민 엔드포인트는 반드시 토큰 인증**
```python
# ✅ 올바른 방법 — X-Admin-Token 헤더 검증
from fastapi import Header, HTTPException
from app.core.config import settings

async def verify_admin(x_admin_token: str = Header(...)):
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")

@router.post("/admin/run-update", dependencies=[Depends(verify_admin)])
async def run_update(): ...
```
- `ADMIN_TOKEN`은 반드시 `.env`에서 불러올 것 (하드코딩 금지)
- 배포 환경에서 어드민 엔드포인트가 외부에 노출되지 않도록 주의

**7. 로그에 URL 쿼리 파라미터(API 키) 노출 금지**
```python
# ❌ 위험 — httpx 에러 객체에 API 키가 포함된 URL이 출력될 수 있음
logger.error(f"요청 실패: {e}")

# ✅ 올바른 방법 — 메시지만 추출, URL은 제외
logger.error(f"요청 실패: {type(e).__name__}: {str(e.args[0])[:200]}")
```

---

### API 키 발급 필요 목록

개발 시작 전 아래 키를 발급해서 .env에 입력해야 합니다.

| API | 발급처 | 비고 |
|-----|--------|------|
| 국토부 실거래가 | https://www.data.go.kr | 무료, 즉시 발급 |
| 청약홈 오픈API | https://www.data.go.kr | 무료, 회원가입 필요 (청약홈 계정 연동) |
| LH청약센터 | https://www.data.go.kr | 무료 |
| 네이버 검색 API | https://developers.naver.com | 무료, 앱 등록 필요 |
| 카카오 API | https://developers.kakao.com | 무료, 앱 등록 필요 |
| Anthropic API | https://console.anthropic.com | 유료 (종량제) |
| Gmail 앱 비밀번호 | Google 계정 설정 | 2단계 인증 필요 |

---

### 주요 제약사항

- **네이버 카페 크롤링 금지** — 약관 위반, 계정 정지 위험
- **개인정보 저장 금지** — DB에 개인 식별 정보 저장 불가
- **API 호출 빈도 제한 준수** — 네이버 API는 초당 10회 제한
- **SQLite는 개발용** — 배포 시 Supabase(PostgreSQL)로 이전 필요

---

### 목업 데이터

API 키 없이 UI 개발 시 `backend/app/core/mock_data.py`에
더미 데이터를 정의하고 `USE_MOCK=true` 환경변수로 전환 가능하게 할 것.

---

### 커밋 메시지 규칙

```
feat: 새 기능 추가
fix: 버그 수정
data: 데이터 수집 관련
ui: 프론트엔드 변경
config: 설정 변경
docs: 문서 수정
```

---

*마지막 업데이트: 2026-05-20 (초기 설계 단계)*
