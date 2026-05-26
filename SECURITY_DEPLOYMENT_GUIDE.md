# 🔒 배포 환경 보안 설정 가이드

> 프로덕션 배포 전 **반드시** 이 가이드의 모든 항목을 완료하세요.
> 마지막 업데이트: 2026-05-26

---

## 📋 배포 전 보안 체크리스트

- [ ] 환경변수 `.env` 파일 설정 완료 및 git 제외 확인
- [ ] ADMIN_TOKEN 강력한 토큰으로 생성
- [ ] CORS 설정 와일드카드 제거
- [ ] API 키 로그 노출 검사
- [ ] HTTPS 리디렉트 설정
- [ ] 데이터베이스 보안 설정 (SQLite → PostgreSQL 마이그레이션)
- [ ] 어드민 엔드포인트 레이트 제한 추가
- [ ] 배포 환경 변수 확인 (USE_MOCK=false)
- [ ] 의존성 버전 고정
- [ ] 배포 후 보안 테스트

---

## 1️⃣ 환경변수 보안

### 1.1 강력한 ADMIN_TOKEN 생성

배포 서버 또는 로컬에서 다음 명령어로 생성:

```bash
# macOS / Linux
openssl rand -hex 32

# 또는 Python 사용
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**출력 예:**
```
a7f3b9c2e1d45f6a8b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2
```

### 1.2 .env 파일 설정 (배포 환경)

```bash
# 공공 API
MOLIT_API_KEY=your_actual_key
APPLYHOME_API_KEY=your_actual_key
LH_API_KEY=your_actual_key

# 네이버 API
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret

# AI
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

# 카카오
KAKAO_ACCESS_TOKEN=your_kakao_token

# 이메일
GMAIL_USER=your-email@gmail.com
GMAIL_APP_PASSWORD=your_16_digit_app_password

# DB (프로덕션: PostgreSQL 권장)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname

# 앱 설정
TZ=Asia/Seoul
USE_MOCK=false                    # ⚠️ 프로덕션에서는 반드시 false

# 보안
ADMIN_TOKEN=a7f3b9c2e1d45f6a8b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2
ALLOWED_ORIGINS=https://yourdomain.com  # 개발용 localhost 제외
```

### 1.3 환경변수 검증

배포 전 다음을 확인:

```bash
# git에 .env 이력이 없는지 확인
git log --oneline --all -- .env

# 결과가 없어야 함 (있으면 git 히스토리에서 제거 필요)
```

---

## 2️⃣ CORS 보안 강화

### 2.1 [backend/main.py](backend/main.py) 수정

**현재 (위험):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],        # ❌ 모든 메서드 허용
    allow_headers=["*"],        # ❌ 모든 헤더 허용
)
```

**변경 (안전):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],      # ✅ 필요한 메서드만 허용
    allow_headers=["Content-Type", "Authorization"],  # ✅ 필요한 헤더만 허용
)
```

---

## 3️⃣ API 키 로그 노출 방지

### 3.1 [backend/app/services/news_service.py] 검토

현재 코드에서 예외 처리가 부분적으로 안전하게 구현되어 있습니다.

**이미 안전한 부분:**
```python
except httpx.HTTPStatusError as e:
    logger.error(f"네이버 API HTTP 오류 {e.response.status_code} ({keyword}/{source_type}): {type(e).__name__}")
```

**추가 확인:** 모든 서비스에서 다음 패턴 사용 여부 확인:
- ❌ `logger.error(f"Error: {e}")` — 전체 예외 객체 로깅
- ✅ `logger.error(f"Error: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")` — 타입과 첫 200자만 로깅

### 3.2 Anthropic API 에러 처리 확인

[backend/app/services/ai_service.py]에서 예외 발생 시:

```python
except Exception as e:
    logger.error(
        f"AI 분석 실패 ({item.get('title', '')[:30]}): "
        f"{type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}"
    )
    results.append(item)
```

**이미 안전하게 구현됨** ✅

---

## 4️⃣ 어드민 엔드포인트 보호 강화

### 4.1 레이트 제한 추가 (선택사항)

프로덕션에서는 어드민 엔드포인트에 레이트 제한을 추가하는 것이 권장됩니다.

**설치:**
```bash
pip install slowapi
```

**[backend/main.py] 수정 (선택):**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# admin 라우터에 적용
from app.api import admin
admin.router = limiter.limit("5/minute")(admin.router)
```

### 4.2 HTTPS 강제 (필수)

배포 플랫폼(Railway)에서 자동으로 HTTPS를 제공하지만, 다음 설정으로 강제:

**[backend/main.py]에 추가:**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["yourdomain.com", "www.yourdomain.com"]
)
```

---

## 5️⃣ 데이터베이스 보안

### 5.1 SQLite → PostgreSQL 마이그레이션 (권장)

**개발 환경:** SQLite (가능)
**프로덕션 환경:** PostgreSQL (필수)

**마이그레이션 단계:**

1. **Supabase 계정 생성** (https://supabase.com)

2. **새 프로젝트 생성:**
   - Database Password 저장
   - Connection String 복사: `postgresql://user:password@host:5432/postgres`

3. **DATABASE_URL 업데이트:**
   ```bash
   # AsyncPG 드라이버 사용
   DATABASE_URL=postgresql+asyncpg://user:password@db.xxxxx.supabase.co:5432/postgres
   ```

4. **의존성 추가:**
   ```bash
   pip install asyncpg
   ```

5. **로컬에서 테스트:**
   ```bash
   cd backend
   export $(cat ../.env | xargs)
   python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"
   ```

### 5.2 데이터 암호화 (선택)

민감한 토큰을 암호화하려면:

```bash
pip install python-jose cryptography
```

[backend/app/models/models.py]에 암호화 필드 추가:
```python
from cryptography.fernet import Fernet

class AppSetting(Base):
    __tablename__ = "app_settings"
    # ... 기존 필드 ...
    
    # 암호화 필드 (선택)
    # encrypted_kakao_token: Mapped[str | None] = mapped_column(String(500))
```

---

## 6️⃣ 의존성 버전 고정

### 6.1 [backend/requirements.txt] 고정 버전 설정

**현재 (위험):**
```
fastapi>=0.111.0
httpx>=0.27.0
```

**변경 (안전):**
```bash
pip freeze > backend/requirements.txt
```

또는 수동으로:
```
fastapi==0.111.0
httpx==0.27.0
sqlalchemy==2.0.36
# ... 등등
```

### 6.2 [frontend/package.json] 락파일 확인

```bash
cd frontend

# package-lock.json이 git에 커밋되어 있는지 확인
git ls-files | grep package-lock.json

# 없으면 생성
npm install --package-lock-only

# git에 추가
git add package-lock.json
git commit -m "feat: add package-lock.json for dependency integrity"
```

---

## 7️⃣ 배포 환경 변수 확인

### 7.1 Railway 배포 설정

Railway 대시보드에서:

1. **Variables 탭 → Edit Variables**

2. 다음 항목 추가:
   ```
   USE_MOCK=false                    # ✅ 프로덕션 데이터 사용
   ADMIN_TOKEN=a7f3b9c2...          # ✅ 강력한 토큰
   ALLOWED_ORIGINS=https://yourdomain.com
   DATABASE_URL=postgresql+asyncpg://...
   MOLIT_API_KEY=...
   # ... 나머지 API 키
   ```

3. **Deploy 버튼 클릭 후 재배포**

### 7.2 배포 후 환경변수 검증

```bash
# Railway 로그에서 확인 (API 키는 보이지 않아야 함)
railway logs

# 헬스체크 엔드포인트 테스트
curl https://yourdomain.com/healthz

# 응답: {"status": "ok", "service": "부산 내집마련 대시보드"}
```

---

## 8️⃣ 보안 헤더 추가 (선택)

### 8.1 [backend/main.py]에 보안 헤더 미들웨어 추가

```python
from fastapi.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

## 9️⃣ 배포 후 보안 검증

### 9.1 CORS 테스트

```bash
# 허용되지 않은 Origin에서 요청 테스트
curl -H "Origin: https://evil.com" \
     -H "Access-Control-Request-Method: DELETE" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS https://yourdomain.com/api/subscriptions -v

# 응답에서 Access-Control-Allow-Origin 헤더가 없어야 함
```

### 9.2 어드민 토큰 테스트

```bash
# 잘못된 토큰으로 요청
curl -X POST https://yourdomain.com/api/admin/run-update \
     -H "X-Admin-Token: wrong-token" \
     -v

# 응답: 403 Forbidden
```

```bash
# 올바른 토큰으로 요청
curl -X POST https://yourdomain.com/api/admin/run-update \
     -H "X-Admin-Token: a7f3b9c2e1d45f6a8b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2" \
     -v

# 응답: 200 OK, {"status": "ok", "message": "전체 업데이트 완료"}
```

### 9.3 환경변수 노출 확인

```bash
# 공개 엔드포인트에서 민감한 정보 유출 확인
curl https://yourdomain.com/api/settings

# 응답에 API 키가 없어야 함
```

### 9.4 HTTPS 강제 확인

```bash
# HTTP 요청을 HTTPS로 리디렉트하는지 확인
curl -I http://yourdomain.com

# 응답: 307 또는 308 Temporary/Permanent Redirect
```

---

## 🚨 배포 직후 모니터링

### 1. 에러 로그 모니터링
```bash
# Railway 대시보드의 Logs 탭에서:
# - 500 에러 확인
# - API 키 또는 민감한 정보 노출 확인
```

### 2. 성능 모니터링
```bash
# 응답 시간이 5초 이상이면 이상 신호
# DB 연결 문제 또는 외부 API 응답 지연 확인
```

### 3. 보안 로그 확인
```bash
# 비정상적인 어드민 요청 시도 확인
# 403 Forbidden 응답이 자주 나면 스캔 공격 가능성
```

---

## 📞 문제 해결

| 문제 | 원인 | 해결책 |
|------|------|--------|
| 배포 후 404 에러 | 프론트엔드 빌드 실패 | Dockerfile 확인, `npm run build` 재실행 |
| CORS 에러 | ALLOWED_ORIGINS 설정 오류 | Railway Variables에서 도메인 확인 |
| DB 연결 실패 | DATABASE_URL 오류 | Supabase 연결 문자열 재확인 |
| API 키 관련 에러 | 환경변수 미설정 | Railway Variables 다시 입력 |
| 어드민 403 에러 | 토큰 불일치 | ADMIN_TOKEN 정확성 재확인 |

---

## 📝 배포 후 체크리스트

배포 완료 후 다음을 확인:

- [ ] 프론트엔드 페이지 로드됨
- [ ] API 엔드포인트 응답 정상 (예: `/api/subscriptions`)
- [ ] HTTPS 자동 리디렉트 작동
- [ ] 어드민 토큰으로 `/api/admin/run-update` 실행 성공
- [ ] 에러 로그에 API 키 미노출
- [ ] CORS 에러 없음
- [ ] 데이터베이스 데이터 정상 저장
- [ ] 카카오/이메일 알림 테스트 성공

---

## 🔗 참고 자료

- [FastAPI 보안 문서](https://fastapi.tiangolo.com/advanced/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Railway 배포 가이드](https://docs.railway.app/)
- [Supabase 시작하기](https://supabase.com/docs)
- [SQLAlchemy 보안](https://docs.sqlalchemy.org/en/14/faq/security.html)

---

**마지막 점검:** 모든 항목이 완료되었다면, 배포를 진행하세요. 🚀
