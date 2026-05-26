import calendar
import hmac
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(tags=["admin"])


async def verify_admin(x_admin_token: str = Header(...)):
    # hmac.compare_digest: 타이밍 공격(timing attack) 방지용 상수 시간 비교
    if not hmac.compare_digest(x_admin_token, settings.ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/admin/run-update", dependencies=[Depends(verify_admin)])
async def run_update():
    """전체 데이터 업데이트 즉시 실행 (테스트용)"""
    from app.scheduler.tasks import daily_full_update
    await daily_full_update()
    return {"status": "ok", "message": "전체 업데이트 완료"}


@router.post("/admin/run-urgent", dependencies=[Depends(verify_admin)])
async def run_urgent():
    """줍줍 긴급 체크 즉시 실행"""
    from app.scheduler.tasks import urgent_check
    await urgent_check()
    return {"status": "ok", "message": "줍줍 긴급 체크 완료"}


class UploadPayload(BaseModel):
    yearmonth: str | None = None
    transactions: list[dict[str, Any]] = []
    subscriptions: list[dict[str, Any]] = []


@router.post("/admin/upload", dependencies=[Depends(verify_admin)])
async def upload_data(payload: UploadPayload):
    """로컬 수집 스크립트에서 데이터를 받아 DB에 저장 (해외 IP 우회용)"""
    from sqlalchemy import delete, select
    from app.core.database import AsyncSessionLocal
    from app.models.models import Transaction, Subscription
    from app.scheduler.tasks import _update_market_stats

    saved = {"transactions": 0, "subscriptions": 0}

    async with AsyncSessionLocal() as db:
        # 실거래가: 해당 월 삭제 후 재적재
        if payload.transactions and payload.yearmonth:
            ym = payload.yearmonth
            year, month = int(ym[:4]), int(ym[4:6])
            _, last_day = calendar.monthrange(year, month)
            await db.execute(
                delete(Transaction).where(
                    Transaction.deal_date >= date(year, month, 1),
                    Transaction.deal_date <= date(year, month, last_day),
                )
            )
            for item in payload.transactions:
                item = dict(item)
                if isinstance(item.get("deal_date"), str):
                    item["deal_date"] = date.fromisoformat(item["deal_date"])
                db.add(Transaction(**item))
            saved["transactions"] = len(payload.transactions)

        # 청약: source_url 기준 중복 제외 후 신규만 저장
        for item in payload.subscriptions:
            item = dict(item)
            if not item.get("source_url"):
                continue
            existing = await db.execute(
                select(Subscription).where(Subscription.source_url == item["source_url"])
            )
            if existing.scalar_one_or_none() is not None:
                continue
            for f in ("application_start", "application_end"):
                if isinstance(item.get(f), str):
                    item[f] = date.fromisoformat(item[f])
                elif item.get(f) is None:
                    item[f] = None
            db.add(Subscription(**item))
            saved["subscriptions"] += 1

        await db.commit()

    # 실거래가 저장 후 시세통계 재계산
    if saved["transactions"]:
        async with AsyncSessionLocal() as db:
            await _update_market_stats(db)

    return {"status": "ok", "saved": saved}
