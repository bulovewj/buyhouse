from datetime import date
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(tags=["transactions"])


class TransactionItem(BaseModel):
    district: str
    dong: str
    apt_name: str
    area_sqm: Optional[float] = None
    floor: Optional[int] = None
    price_won: int
    deal_date: date
    build_year: Optional[int] = None

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[TransactionItem]


@router.get("/transactions", response_model=PaginatedResponse)
async def get_transactions(
    district: Optional[str] = Query(None),
    dong: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    from app.services.transaction_service import fetch_transactions
    items = await fetch_transactions()

    if district:
        items = [i for i in items if i.get("district") == district]
    if dong:
        items = [i for i in items if dong in i.get("dong", "")]

    # 거래일 최신순
    items.sort(key=lambda x: x.get("deal_date") or date.min, reverse=True)

    total = len(items)
    start = (page - 1) * limit
    paged = items[start: start + limit]

    return PaginatedResponse(total=total, page=page, limit=limit, items=paged)
