import logging
from datetime import date, timedelta

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



_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BuyHouseDashboard/1.0)"}
_ODCLOUD_BASE = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1"


async def _fetch_applyhome() -> list:
    """한국부동산원 청약홈 분양정보 API (api.odcloud.kr) — 부산 APT·무순위 분양공고"""
    today = date.today()
    six_months_ago = (today - timedelta(days=180)).isoformat()
    items = []

    endpoints = [
        ("getAPTLttotPblancDetail", "청약"),
        ("getRemndrLttotPblancDetail", "줍줍"),
    ]

    async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
        for op, default_type in endpoints:
            res = await client.get(
                f"{_ODCLOUD_BASE}/{op}",
                params={
                    "page": 1, "perPage": 100,
                    "serviceKey": settings.APPLYHOME_API_KEY,
                    "returnType": "json",
                    "cond[SUBSCRPT_AREA_CODE_NM::EQ]": "부산",
                    "cond[RCRIT_PBLANC_DE::GTE]": six_months_ago,
                },
            )
            res.raise_for_status()
            for raw in res.json().get("data", []):
                end_date = _parse_date(raw.get("RCEPT_ENDDE", ""))
                if end_date and end_date < today:
                    continue  # 접수 마감된 건 제외
                dtl = raw.get("HOUSE_DTL_SECD_NM", "")
                sub_type = "줍줍" if "무순위" in dtl else default_type
                supply_count = None
                try:
                    if sc := raw.get("TOT_SUPLY_HSHLDCO"):
                        supply_count = int(sc)
                except (ValueError, TypeError):
                    pass
                items.append({
                    "title": raw.get("HOUSE_NM", ""),
                    "type": sub_type,
                    "location": raw.get("HSSPLY_ADRES", ""),
                    "supply_count": supply_count,
                    "price_min": None,
                    "price_max": None,
                    "application_start": _parse_date(raw.get("RCEPT_BGNDE", "")),
                    "application_end": end_date,
                    "source_url": raw.get("PBLANC_URL"),
                    "is_notified": False,
                })

    logger.info(f"청약홈 API: 부산 {len(items)}건 수집")
    return items


async def _fetch_lh() -> list:
    """LH 청약센터 공지사항 목록 조회 — 부산울산지역본부 주택 공고
    서비스: apis.data.go.kr/B552555/lhNoticeInfo1/getNoticeInfo1
    """
    url = "https://apis.data.go.kr/B552555/lhNoticeInfo1/getNoticeInfo1"
    params = {
        "serviceKey": settings.LH_API_KEY,
        "SL_BBS_KD_CD": "03",
        "PG_SZ": 50,
        "PAGE": 1,
    }
    async with httpx.AsyncClient(timeout=15, headers=_HEADERS) as client:
        res = await client.get(url, params=params)
        res.raise_for_status()

    data = res.json()
    ds_list = next((x.get("dsList", []) for x in data if "dsList" in x), [])

    items = []
    for raw in ds_list:
        if "부산" not in raw.get("DEP_NM", ""):
            continue
        title = raw.get("BBS_TL", "")
        if not title:
            continue
        ais_tp = raw.get("AIS_TP_CD_NM", "")
        if any(k in ais_tp for k in ["용지", "시설", "상가", "토지"]):
            continue  # 주택 외 공지 제외
        sub_type = "행복주택" if "행복" in ais_tp else "공공임대"
        link_url = raw.get("LINK_URL") or ""
        bbs_sn = raw.get("BBS_SN", "")
        source = link_url or (
            f"https://apply.lh.or.kr/lhapply/apply/noti/an/view.do?bbsSn={bbs_sn}" if bbs_sn else None
        )
        items.append({
            "title": title,
            "type": sub_type,
            "location": f"부산 ({raw.get('DEP_NM', '')})",
            "supply_count": None,
            "price_min": None,
            "price_max": None,
            "application_start": _parse_date(raw.get("BBS_WOU_DTTM", "")),
            "application_end": None,
            "source_url": source,
            "is_notified": False,
        })

    logger.info(f"LH API: 부산 {len(items)}건 수집")
    return items
