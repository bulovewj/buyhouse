from datetime import date
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["market"])


class DistrictStat(BaseModel):
    district: str
    avg_price: Optional[int] = None
    avg_jeonse_price: Optional[int] = None
    jeonse_rate: Optional[float] = None
    unsold_count: Optional[int] = None
    transaction_volume: Optional[int] = None

    class Config:
        from_attributes = True


class MarketStatsResponse(BaseModel):
    stat_date: date
    districts: list[DistrictStat]


@router.get("/market-stats", response_model=MarketStatsResponse)
async def get_market_stats():
    from app.services.market_stats_service import fetch_market_stats
    items = await fetch_market_stats()

    stat_date = items[0]["stat_date"] if items else date.today()
    # 평균 매매가 내림차순 정렬
    items.sort(key=lambda x: x.get("avg_price") or 0, reverse=True)

    return MarketStatsResponse(stat_date=stat_date, districts=items)
