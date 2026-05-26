import logging
import xml.etree.ElementTree as ET
from datetime import date

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_subscriptions(type_filter: str = None) -> list:
    """API 라우터용: USE_MOCK=True면 목업, 아니면 DB에서 읽기"""
    if settings.USE_MOCK:
        from app.core.mock_data import MOCK_SUBSCRIPTIONS
        data = list(MOCK_SUBSCRIPTIONS)
        if type_filter:
            data = [s for s in data if s["type"] == type_filter]
        return data

    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.models import Subscription

    async with AsyncSessionLocal() as db:
        q = select(Subscription).order_by(Subscription.application_end)
        if type_filter:
            q = q.where(Subscription.type == type_filter)
        result = await db.execute(q)
        return [_to_dict(r) for r in result.scalars().all()]


async def fetch_subscriptions_from_api() -> list:
    """스케줄러 전용: 외부 API에서 청약·공고 수집"""
    results = []
    try:
        results += await _fetch_applyhome()
    except httpx.HTTPStatusError as e:
        logger.error(f"청약홈 HTTP 오류 {e.response.status_code}: {type(e).__name__}")
    except httpx.TimeoutException:
        logger.error("청약홈 요청 타임아웃")
    except Exception as e:
        logger.error(f"청약홈 수집 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")

    try:
        results += await _fetch_lh()
    except httpx.HTTPStatusError as e:
        logger.error(f"LH API HTTP 오류 {e.response.status_code}: {type(e).__name__}")
    except httpx.TimeoutException:
        logger.error("LH API 요청 타임아웃")
    except Exception as e:
        logger.error(f"LH 수집 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")

    return results


def _to_dict(r) -> dict:
    return {
        "title": r.title,
        "type": r.type,
        "location": r.location,
        "supply_count": r.supply_count,
        "price_min": r.price_min,
        "price_max": r.price_max,
        "application_start": r.application_start,
        "application_end": r.application_end,
        "source_url": r.source_url,
        "is_notified": r.is_notified,
    }


def _parse_date(s: str) -> date | None:
    if not s:
        return None
    s = s.strip().replace("-", "").replace("/", "").replace(".", "")
    if len(s) == 8:
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        except ValueError:
            pass
    return None


def _xtext(item, *tags) -> str:
    """여러 가능한 태그명을 순서대로 시도해 첫 번째 값 반환"""
    for tag in tags:
        val = item.findtext(tag)
        if val and val.strip():
            return val.strip()
    return ""


async def _fetch_applyhome() -> list:
    """청약홈 오픈API (data.go.kr) — 부산 아파트 분양공고"""
    url = "https://apis.data.go.kr/B552555/APTInfoService/getAPTLttotPblancMdList"
    params = {
        "serviceKey": settings.APPLYHOME_API_KEY,
        "sidoNm": "부산광역시",
        "numOfRows": 100,
        "pageNo": 1,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()

    root = ET.fromstring(res.text)
    result_code = root.findtext(".//resultCode") or ""
    if result_code and result_code not in ("00", "0000"):
        logger.warning(f"청약홈 API 오류: {result_code} / {root.findtext('.//resultMsg')}")
        return []

    items = []
    for item in root.findall(".//item"):
        t = lambda *tags: _xtext(item, *tags)  # noqa: E731

        sido = t("SIDO_NM", "sidoNm")
        if "부산" not in sido:
            continue

        title = t("HOUSE_NM", "housNm")
        if not title:
            continue

        house_secd = t("HOUSE_SECD_NM", "houseSecd", "RENT_SECD_NM")
        sub_type = "줍줍" if "무순위" in house_secd else "청약"

        supply_count = None
        try:
            sc = t("TOT_SUPLY_HSHLDCO", "totSuplyHshldco")
            if sc:
                supply_count = int(sc.replace(",", ""))
        except ValueError:
            pass

        manage_no = t("HOUSE_MANAGE_NO", "pnahouseManageNo")
        sgg = t("SGG_NM", "sggNm")
        emd = t("EML_NM", "emdNm")

        items.append({
            "title": title,
            "type": sub_type,
            "location": f"부산 {sgg} {emd}".strip(),
            "supply_count": supply_count,
            "price_min": None,
            "price_max": None,
            "application_start": _parse_date(t("RCEPT_BGNDE", "rcptBgnDe")),
            "application_end": _parse_date(t("RCEPT_ENDDE", "rcptEndDe")),
            "source_url": (
                f"https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancListForm.do?houseManageNo={manage_no}"
                if manage_no else None
            ),
            "is_notified": False,
        })

    logger.info(f"청약홈 API: 부산 {len(items)}건 수집")
    return items


async def _fetch_lh() -> list:
    """LH 오픈API (data.go.kr) — 부산 행복주택·공공임대 공고"""
    url = "https://apis.data.go.kr/B552555/lhNoticeDtlInfo1/lhNoticeDtlInfo1"
    params = {
        "serviceKey": settings.LH_API_KEY,
        "PG_SZ": 100,
        "PAGE": 1,
        "CNP_CD": "26",  # 부산 지역 코드
    }
    async with httpx.AsyncClient(timeout=15) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()

    try:
        data = res.json()
    except Exception:
        logger.warning("LH API: JSON 파싱 실패 (응답 형식 확인 필요)")
        return []

    raw_items = data.get("dsList") or data.get("data") or []
    if not raw_items and isinstance(data, list):
        raw_items = data

    items = []
    for raw in raw_items:
        title = raw.get("AIS_TP_NM") or raw.get("PAN_NM") or ""
        if not title:
            continue

        sido = raw.get("CNP_CD_NM") or ""
        if sido and "부산" not in sido:
            continue

        ais_tp = raw.get("AIS_TP_CD_NM") or raw.get("AIS_TP_NM") or ""
        sub_type = "행복주택" if "행복" in ais_tp else "공공임대"

        supply_count = None
        try:
            sc = raw.get("TOT_SUPLY_CNT") or raw.get("SUPLY_CNT") or ""
            if sc:
                supply_count = int(str(sc).replace(",", ""))
        except (ValueError, TypeError):
            pass

        pan_id = raw.get("PAN_ID") or raw.get("PBLANC_NO") or ""
        items.append({
            "title": title,
            "type": sub_type,
            "location": f"부산 {raw.get('SGG_NM', '')}".strip(),
            "supply_count": supply_count,
            "price_min": None,
            "price_max": None,
            "application_start": _parse_date(str(raw.get("PAN_SS") or raw.get("RCEPT_BGNDE") or "")),
            "application_end": _parse_date(str(raw.get("PAN_DE") or raw.get("RCEPT_ENDDE") or "")),
            "source_url": (
                f"https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWtanNoList.do?sc={pan_id}"
                if pan_id else None
            ),
            "is_notified": False,
        })

    logger.info(f"LH API: 부산 {len(items)}건 수집")
    return items
