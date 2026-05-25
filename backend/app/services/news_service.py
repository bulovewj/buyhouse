import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SEARCH_KEYWORDS = ["부산 아파트", "부산 청약", "부산 부동산", "부산 재개발", "부산 분양", "부산 전세"]


async def fetch_news() -> list:
    if settings.USE_MOCK:
        from app.core.mock_data import MOCK_NEWS
        return MOCK_NEWS

    seen_urls: set[str] = set()
    results = []

    for keyword in SEARCH_KEYWORDS:
        for source_type, endpoint in [("뉴스", "news"), ("블로그", "blog")]:
            try:
                items = await _fetch_naver(keyword, endpoint)
                for item in items:
                    if item["source_url"] not in seen_urls:
                        seen_urls.add(item["source_url"])
                        item["source_type"] = source_type
                        results.append(item)
            except httpx.HTTPStatusError as e:
                logger.error(f"네이버 API HTTP 오류 {e.response.status_code} ({keyword}/{source_type}): {type(e).__name__}")
            except httpx.TimeoutException as e:
                logger.error(f"네이버 API 타임아웃 ({keyword}): {type(e).__name__}")
            except Exception as e:
                logger.error(f"뉴스 수집 실패 ({keyword}): {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")

    return results


async def _fetch_naver(query: str, endpoint: str) -> list:
    url = f"https://openapi.naver.com/v1/search/{endpoint}.json"
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": 10, "sort": "date"}
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(url, headers=headers, params=params)
        res.raise_for_status()
    # TODO: 응답 파싱 → dict 변환
    return []
