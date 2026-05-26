import calendar
import logging
import xml.etree.ElementTree as ET
from datetime import date
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

# 부산 구군 법정동 코드 → 구 이름
BUSAN_LAWD_CODES: dict[str, str] = {
    "26110": "중구",
    "26140": "서구",
    "26170": "동구",
    "26200": "영도구",
    "26230": "부산진구",
    "26260": "동래구",
    "26290": "남구",
    "26320": "북구",
    "26350": "해운대구",
    "26380": "사하구",
    "26410": "금정구",
    "26440": "강서구",
    "26470": "연제구",
    "26500": "수영구",
    "26530": "사상구",
    "26710": "기장군",
}


async def fetch_transactions(yearmonth: str = None) -> list:
    """API 라우터용: USE_MOCK=True면 목업, 아니면 DB에서 읽기"""
    if settings.USE_MOCK:
        from app.core.mock_data import MOCK_TRANSACTIONS
        return list(MOCK_TRANSACTIONS)

    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.models import Transaction

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Transaction).order_by(Transaction.deal_date.desc())
        )
        return [
            {
                "district": r.district,
                "dong": r.dong,
                "apt_name": r.apt_name,
                "area_sqm": r.area_sqm,
                "floor": r.floor,
                "price_won": r.price_won,
                "deal_date": r.deal_date,
                "build_year": r.build_year,
            }
            for r in result.scalars().all()
        ]


async def fetch_transactions_from_api(yearmonth: str = None) -> list:
    """스케줄러 전용: 국토부 API에서 실거래가 수집"""
    if yearmonth is None:
        today = date.today()
        yearmonth = f"{today.year}{today.month:02d}"

    results = []
    for code, district_name in BUSAN_LAWD_CODES.items():
        try:
            items = await _fetch_molit(code, yearmonth, district_name)
            results += items
        except httpx.HTTPStatusError as e:
            logger.error(f"국토부 HTTP 오류 {e.response.status_code} ({district_name}): {type(e).__name__}")
        except httpx.TimeoutException:
            logger.error(f"국토부 API 타임아웃 ({district_name})")
        except Exception as e:
            logger.error(f"실거래가 수집 실패 ({district_name}): {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")

    logger.info(f"국토부 API: 부산 실거래가 {len(results)}건 수집")
    return results


def _get_month_range(yearmonth: str) -> tuple[date, date]:
    year, month = int(yearmonth[:4]), int(yearmonth[4:6])
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, 1), date(year, month, last_day)


_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BuyHouseDashboard/1.0)"}


async def _fetch_molit(lawd_cd: str, deal_ymd: str, district_name: str) -> list:
    """국토부 아파트 매매 실거래가 XML 파싱 (표준 API, 영문 필드명)"""
    url = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
    params = {
        "serviceKey": settings.MOLIT_API_KEY,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "numOfRows": 1000,
        "pageNo": 1,
    }
    async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()

    root = ET.fromstring(res.text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code and result_code not in ("00", "0000", "000"):
        logger.warning(f"국토부 API 오류 ({district_name}): {result_code} / {root.findtext('.//resultMsg')}")
        return []

    items = []
    for item in root.findall(".//item"):
        def t(tag): return (item.findtext(tag) or "").strip()  # noqa: E731

        price_raw = t("dealAmount").replace(",", "").replace(" ", "")
        if not price_raw:
            continue
        try:
            price_won = int(price_raw) * 10_000  # 만원 → 원
        except ValueError:
            continue

        try:
            deal_date = date(int(t("dealYear")), int(t("dealMonth")), int(t("dealDay")))
        except (ValueError, TypeError):
            continue

        area_sqm = None
        try:
            area_sqm = float(t("excluUseAr"))
        except (ValueError, TypeError):
            pass

        floor = None
        try:
            floor = int(t("floor"))
        except (ValueError, TypeError):
            pass

        build_year = None
        try:
            build_year = int(t("buildYear"))
        except (ValueError, TypeError):
            pass

        items.append({
            "district": district_name,
            "dong": t("umdNm"),
            "apt_name": t("aptNm"),
            "area_sqm": area_sqm,
            "floor": floor,
            "price_won": price_won,
            "deal_date": deal_date,
            "build_year": build_year,
        })

    return items
