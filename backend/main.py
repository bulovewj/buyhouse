import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("DB 초기화 완료")

    from app.scheduler.tasks import scheduler
    scheduler.start()
    logger.info("스케줄러 시작")

    yield

    scheduler.shutdown()
    logger.info("스케줄러 종료")


app = FastAPI(title="부산 내집마련 대시보드", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import admin, subscriptions, transactions, news, market, settings, notifications, calculator  # noqa: E402

app.include_router(subscriptions.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(calculator.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/healthz")
async def health():
    return {"status": "ok", "service": "부산 내집마련 대시보드"}


# 빌드된 프론트엔드 정적 파일 서빙 (배포 환경)
# API 라우터보다 뒤에 등록해야 /api/* 우선순위가 유지된다.
# SPA 특성상 /assets/* 만 StaticFiles로 처리하고,
# 나머지 경로(React Router 경로 포함)는 index.html 폴백으로 처리한다.
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    _ASSETS_DIR = os.path.join(_STATIC_DIR, "assets")
    if os.path.isdir(_ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(_STATIC_DIR, "index.html"))
