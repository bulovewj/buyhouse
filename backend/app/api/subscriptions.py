from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(tags=["subscriptions"])


class SubscriptionItem(BaseModel):
    title: str
    type: str
    location: Optional[str] = None
    supply_count: Optional[int] = None
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    application_start: Optional[date] = None
    application_end: Optional[date] = None
    source_url: Optional[str] = None
    is_notified: bool = False

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[SubscriptionItem]


@router.get("/subscriptions", response_model=PaginatedResponse)
async def get_subscriptions(
    type: Optional[str] = Query(None, description="청약|줍줍|행복주택|공공임대"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    from app.services.subscription_service import fetch_subscriptions
    items = await fetch_subscriptions(type_filter=type)

    today = date.today()
    # 마감일 오름차순 정렬 (마감 임박 먼저), 날짜 없는 항목은 뒤로
    items.sort(key=lambda x: x.get("application_end") or date(9999, 12, 31))

    total = len(items)
    start = (page - 1) * limit
    paged = items[start: start + limit]

    return PaginatedResponse(total=total, page=page, limit=limit, items=paged)
