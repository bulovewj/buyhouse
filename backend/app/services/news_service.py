import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

SEARCH_KEYWORDS = ["부산 아파트", "부산 청약", "부산 부동산", "부산 재개발", "부산 분양", "부산 전세"]

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    return (
        _HTML_TAG_RE.sub("", s)
        .replace("&quot;", '"')
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .strip()
    )


async def fetch_news() -> list:
    """API 라우터용: USE_MOCK=True면 목업, 아니면 DB에서 읽기"""
    if settings.USE_MOCK:
        from app.core.mock_data import MOCK_NEWS
        return list(MOCK_NEWS)

    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.models import NewsReaction

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsReaction).order_by(NewsReaction.published_at.desc())
        )
        return [
            {
                "title": r.title,
                "summary": r.summary,
                "source_url": r.source_url,
                "source_type": r.source_type,
                "sentiment": r.sentiment,
                "sentiment_score": r.sentiment_score,
                "published_at": r.published_at,
            }
            for r in result.scalars().all()
        ]


async def fetch_news_from_api() -> list:
    """스케줄러 전용: 네이버 검색 API에서 뉴스·블로그 수집"""
    seen_urls: set[str] = set()
    results = []

    for keyword in SEARCH_KEYWORDS:
        for source_type, endpoint in [("뉴스", "news"), ("블로그", "blog")]:
            try:
                items = await _fetch_naver(keyword, endpoint, source_type)
                for item in items:
                    if item["source_url"] not in seen_urls:
                        seen_urls.add(item["source_url"])
                        results.append(item)
            except httpx.HTTPStatusError as e:
                logger.error(f"네이버 API HTTP 오류 {e.response.status_code} ({keyword}/{source_type}): {type(e).__name__}")
            except httpx.TimeoutException:
                logger.error(f"네이버 API 타임아웃 ({keyword})")
            except Exception as e:
                logger.error(f"뉴스 수집 실패 ({keyword}): {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")

    logger.info(f"네이버 API: 뉴스·블로그 {len(results)}건 수집")
    return results


async def _fetch_naver(query: str, endpoint: str, source_type: str) -> list:
    url = f"https://openapi.naver.com/v1/search/{endpoint}.json"
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": 10, "sort": "date"}
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(url, headers=headers, params=params)
        res.raise_for_status()

    items = []
    for raw in res.json().get("items", []):
        title = _strip_html(raw.get("title", ""))
        # 블로그는 link, 뉴스는 originallink 우선 사용
        link = raw.get("originallink") or raw.get("link") or ""
        if not title or not link:
            continue

        pub_dt: datetime | None = None
        try:
            pub_dt = parsedate_to_datetime(raw.get("pubDate", "")).astimezone(KST)
        except Exception:
            pub_dt = datetime.now(KST)

        items.append({
            "title": title,
            "summary": _strip_html(raw.get("description", "")) or None,
            "source_url": link,
            "source_type": source_type,
            "sentiment": None,       # AI 분석은 별도 단계
            "sentiment_score": None,
            "published_at": pub_dt,
        })

    return items
