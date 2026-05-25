import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_subscriptions(type_filter: str = None) -> list:
    if settings.USE_MOCK:
        from app.core.mock_data import MOCK_SUBSCRIPTIONS
        data = MOCK_SUBSCRIPTIONS
        if type_filter:
            data = [s for s in data if s["type"] == type_filter]
        return data

    results = []
    try:
        results += await _fetch_applyhome()
    except httpx.HTTPStatusError as e:
        logger.error(f"청약홈 HTTP 오류 {e.response.status_code}: {type(e).__name__}")
    except httpx.TimeoutException as e:
        logger.error(f"청약홈 요청 타임아웃: {type(e).__name__}")
    except Exception as e:
        logger.error(f"청약홈 수집 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")

    try:
        results += await _fetch_lh()
    except httpx.HTTPStatusError as e:
        logger.error(f"LH API HTTP 오류 {e.response.status_code}: {type(e).__name__}")
    except httpx.TimeoutException as e:
        logger.error(f"LH API 요청 타임아웃: {type(e).__name__}")
    except Exception as e:
        logger.error(f"LH 수집 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")

    if type_filter:
        results = [s for s in results if s["type"] == type_filter]
    return results


async def _fetch_applyhome() -> list:
    # 청약홈 오픈API — 부산 지역 필터 (시도코드: 26)
    url = "https://www.applyhome.co.kr/api/applyhomeapi/publicRent"
    params = {
        "serviceKey": settings.APPLYHOME_API_KEY,
        "sido": "부산",
        "numOfRows": 100,
        "pageNo": 1,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()
    # TODO: 실제 응답 파싱
    return []


async def _fetch_lh() -> list:
    # LH 공공데이터 API — 부산 임대주택 공고
    url = "https://api.lh.or.kr/lhOpenApi/services/rest/RentInfoService/getRentInfo"
    params = {
        "serviceKey": settings.LH_API_KEY,
        "sido_nm": "부산광역시",
        "numOfRows": 100,
        "pageNo": 1,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()
    # TODO: 실제 응답 파싱
    return []
