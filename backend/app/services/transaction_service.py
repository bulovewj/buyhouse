import logging
from datetime import date
from zoneinfo import ZoneInfo
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")


async def fetch_transactions(yearmonth: str = None) -> list:
    if settings.USE_MOCK:
        from app.core.mock_data import MOCK_TRANSACTIONS
        return MOCK_TRANSACTIONS

    if yearmonth is None:
        today = date.today()
        yearmonth = f"{today.year}{today.month:02d}"

    results = []
    # 부산 구군 법정동 코드 (26 시작)
    busan_lawd_codes = [
        "26110", "26140", "26170", "26200", "26230",
        "26260", "26290", "26320", "26350", "26380",
        "26410", "26440", "26470", "26500", "26530", "26710",
    ]
    for code in busan_lawd_codes:
        try:
            results += await _fetch_molit(code, yearmonth)
        except httpx.HTTPStatusError as e:
            logger.error(f"국토부 API HTTP 오류 {e.response.status_code} (코드:{code}): {type(e).__name__}")
        except httpx.TimeoutException as e:
            logger.error(f"국토부 API 타임아웃 (코드:{code}): {type(e).__name__}")
        except Exception as e:
            logger.error(f"실거래가 수집 실패 (코드:{code}): {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")

    return results


async def _fetch_molit(lawd_cd: str, deal_ymd: str) -> list:
    url = "http://openapi.molit.go.kr/OpenAPI_ToolInstallPackage/service/rest/RTMSOBJSvc/getRTMSDataSvcAptTradeDev"
    params = {
        "serviceKey": settings.MOLIT_API_KEY,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "numOfRows": 1000,
        "pageNo": 1,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()
    # TODO: XML 응답 파싱 → dict 변환
    return []
