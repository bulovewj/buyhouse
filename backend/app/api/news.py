from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(tags=["news"])

POLICY_KEYWORDS = ["정책", "규제", "LTV", "DSR", "특별공급", "세금", "취득세", "금리"]


class NewsItem(BaseModel):
    title: str
    summary: Optional[str] = None
    source_url: str
    source_type: str
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[NewsItem]


@router.get("/news", response_model=PaginatedResponse)
async def get_news(
    sentiment: Optional[str] = Query(None, description="positive|negative|neutral"),
    source_type: Optional[str] = Query(None, description="뉴스|블로그"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    from app.services.news_service import fetch_news
    items = await fetch_news()

    if sentiment:
        items = [i for i in items if i.get("sentiment") == sentiment]
    if source_type:
        items = [i for i in items if i.get("source_type") == source_type]

    total = len(items)
    start = (page - 1) * limit
    paged = items[start: start + limit]

    return PaginatedResponse(total=total, page=page, limit=limit, items=paged)


@router.get("/policy-news", response_model=PaginatedResponse)
async def get_policy_news(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    from app.services.news_service import fetch_news
    items = await fetch_news()

    policy_items = [
        i for i in items
        if any(kw in i.get("title", "") for kw in POLICY_KEYWORDS)
    ]

    total = len(policy_items)
    start = (page - 1) * limit
    paged = policy_items[start: start + limit]

    return PaginatedResponse(total=total, page=page, limit=limit, items=paged)
