#!/usr/bin/env python3
"""
부산 내집마련 대시보드 — 로컬 데이터 수집 스크립트
Mac(한국 IP)에서 실행 → Railway DB에 데이터 업로드

사용법:
    python collect.py              # 이번 달 실거래가 + 청약 수집
    python collect.py --month 202504   # 특정 월 실거래가 수집

의존성: pip install httpx python-dotenv
"""

import argparse
import asyncio
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

MOLIT_KEY      = os.getenv("MOLIT_API_KEY", "")
APPLYHOME_KEY  = os.getenv("APPLYHOME_API_KEY", "")
LH_KEY         = os.getenv("LH_API_KEY", "")
NAVER_ID       = os.getenv("NAVER_CLIENT_ID", "")
NAVER_SECRET   = os.getenv("NAVER_CLIENT_SECRET", "")
RAILWAY_URL    = os.getenv("RAILWAY_URL", "https://buyhouse-production.up.railway.app")
ADMIN_TOKEN    = os.getenv("ADMIN_TOKEN", "")

KST = ZoneInfo("Asia/Seoul")
_HTML_TAG_RE = re.compile(r"<[^>]+>")

NEWS_KEYWORDS = ["부산 아파트", "부산 청약", "부산 부동산", "부산 재개발", "부산 분양", "부산 전세"]

UA = {"User-Agent": "Mozilla/5.0 (compatible; BuyHouseDashboard/1.0)"}

BUSAN_LAWD = {
    "26110": "중구",   "26140": "서구",   "26170": "동구",   "26200": "영도구",
    "26230": "부산진구", "26260": "동래구", "26290": "남구",   "26320": "북구",
    "26350": "해운대구", "26380": "사하구", "26410": "금정구", "26440": "강서구",
    "26470": "연제구",  "26500": "수영구", "26530": "사상구", "26710": "기장군",
}


def _parse_date(s: str) -> str | None:
    if not s:
        return None
    s = str(s).strip().replace("-", "").replace("/", "").replace(".", "")
    if len(s) == 8:
        try:
            return date(int(s[:4]), int(s[4:6]), int(s[6:8])).isoformat()
        except ValueError:
            pass
    return None


async def collect_transactions(yearmonth: str) -> list[dict]:
    results = []
    async with httpx.AsyncClient(timeout=30, headers=UA) as client:
        for code, name in BUSAN_LAWD.items():
            try:
                res = await client.get(
                    "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
                    params={"serviceKey": MOLIT_KEY, "LAWD_CD": code,
                            "DEAL_YMD": yearmonth, "numOfRows": 1000, "pageNo": 1},
                )
                res.raise_for_status()
                root = ET.fromstring(res.text)
                rc = root.findtext(".//resultCode") or ""
                if rc and rc not in ("00", "000", "0000"):
                    logger.warning(f"  {name}: API 오류 {rc}")
                    continue

                before = len(results)
                for item in root.findall(".//item"):
                    def t(tag): return (item.findtext(tag) or "").strip()  # noqa: E731
                    price_raw = t("dealAmount").replace(",", "").replace(" ", "")
                    if not price_raw:
                        continue
                    try:
                        price_won = int(price_raw) * 10_000
                        deal_date = date(int(t("dealYear")), int(t("dealMonth")), int(t("dealDay")))
                    except (ValueError, TypeError):
                        continue
                    area_sqm = None
                    try: area_sqm = float(t("excluUseAr"))
                    except (ValueError, TypeError): pass
                    floor = None
                    try: floor = int(t("floor"))
                    except (ValueError, TypeError): pass
                    build_year = None
                    try: build_year = int(t("buildYear"))
                    except (ValueError, TypeError): pass

                    results.append({
                        "district": name, "dong": t("umdNm"), "apt_name": t("aptNm"),
                        "area_sqm": area_sqm, "floor": floor, "price_won": price_won,
                        "deal_date": deal_date.isoformat(), "build_year": build_year,
                    })
                logger.info(f"  {name}: {len(results) - before}건")
            except httpx.HTTPStatusError as e:
                logger.warning(f"  {name}: HTTP {e.response.status_code}")
            except Exception as e:
                logger.warning(f"  {name}: {e}")

    logger.info(f"실거래가 총 {len(results)}건 수집 완료")
    return results


async def collect_subscriptions() -> list[dict]:
    results = []
    today = date.today()
    six_months_ago = (today - timedelta(days=180)).isoformat()
    odcloud_base = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1"

    # 한국부동산원 청약홈 분양정보 (APT + 무순위)
    for op, default_type in [("getAPTLttotPblancDetail", "청약"), ("getRemndrLttotPblancDetail", "줍줍")]:
        before = len(results)
        try:
            async with httpx.AsyncClient(timeout=30, headers=UA) as client:
                res = await client.get(
                    f"{odcloud_base}/{op}",
                    params={
                        "page": 1, "perPage": 100,
                        "serviceKey": APPLYHOME_KEY,
                        "returnType": "json",
                        "cond[SUBSCRPT_AREA_CODE_NM::EQ]": "부산",
                        "cond[RCRIT_PBLANC_DE::GTE]": six_months_ago,
                    },
                )
                res.raise_for_status()
                for raw in res.json().get("data", []):
                    end_date = _parse_date(raw.get("RCEPT_ENDDE", ""))
                    if end_date and date.fromisoformat(end_date) < today:
                        continue  # 접수 마감된 건 제외
                    dtl = raw.get("HOUSE_DTL_SECD_NM", "")
                    sub_type = "줍줍" if "무순위" in dtl else default_type
                    supply_count = None
                    try:
                        if sc := raw.get("TOT_SUPLY_HSHLDCO"):
                            supply_count = int(sc)
                    except (ValueError, TypeError):
                        pass
                    results.append({
                        "title": raw.get("HOUSE_NM", ""),
                        "type": sub_type,
                        "location": raw.get("HSSPLY_ADRES", ""),
                        "supply_count": supply_count,
                        "price_min": None, "price_max": None,
                        "application_start": _parse_date(raw.get("RCEPT_BGNDE", "")),
                        "application_end": end_date,
                        "source_url": raw.get("PBLANC_URL"),
                        "is_notified": False,
                    })
            logger.info(f"청약홈 {op}: {len(results) - before}건 수집")
        except httpx.HTTPStatusError as e:
            logger.warning(f"청약홈 {op} HTTP {e.response.status_code} — 건너뜀")
        except Exception as e:
            logger.warning(f"청약홈 {op} 수집 실패: {e}")

    # LH 청약센터 공지사항 (부산울산지역본부)
    lh_before = len(results)
    try:
        async with httpx.AsyncClient(timeout=30, headers=UA) as client:
            res = await client.get(
                "https://apis.data.go.kr/B552555/lhNoticeInfo1/getNoticeInfo1",
                params={"serviceKey": LH_KEY, "SL_BBS_KD_CD": "03", "PG_SZ": 50, "PAGE": 1},
            )
            res.raise_for_status()
            data = res.json()
            ds_list = next((x.get("dsList", []) for x in data if "dsList" in x), [])
            for raw in ds_list:
                if "부산" not in raw.get("DEP_NM", ""):
                    continue
                title = raw.get("BBS_TL", "")
                if not title:
                    continue
                ais_tp = raw.get("AIS_TP_CD_NM", "")
                if any(k in ais_tp for k in ["용지", "시설", "상가", "토지"]):
                    continue
                bbs_sn = raw.get("BBS_SN", "")
                link_url = raw.get("LINK_URL") or ""
                source = link_url or (
                    f"https://apply.lh.or.kr/lhapply/apply/noti/an/view.do?bbsSn={bbs_sn}" if bbs_sn else None
                )
                results.append({
                    "title": title,
                    "type": "행복주택" if "행복" in ais_tp else "공공임대",
                    "location": f"부산 ({raw.get('DEP_NM', '')})",
                    "supply_count": None, "price_min": None, "price_max": None,
                    "application_start": _parse_date(raw.get("BBS_WOU_DTTM", "")),
                    "application_end": None,
                    "source_url": source,
                    "is_notified": False,
                })
        logger.info(f"LH 공지사항: {len(results) - lh_before}건 수집 (부산)")
    except httpx.HTTPStatusError as e:
        logger.warning(f"LH HTTP {e.response.status_code} — 건너뜀")
    except Exception as e:
        logger.warning(f"LH 수집 실패: {e}")

    logger.info(f"청약·공고 총 {len(results)}건 수집 완료")
    return results


async def collect_news() -> list[dict]:
    if not NAVER_ID or not NAVER_SECRET:
        logger.warning("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 없음 — 뉴스 수집 건너뜀")
        return []

    def _strip(s: str) -> str:
        return _HTML_TAG_RE.sub("", s).replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").strip()

    seen_urls: set[str] = set()
    results = []

    async with httpx.AsyncClient(timeout=10, headers={"X-Naver-Client-Id": NAVER_ID, "X-Naver-Client-Secret": NAVER_SECRET}) as client:
        for keyword in NEWS_KEYWORDS:
            for source_type, endpoint in [("뉴스", "news"), ("블로그", "blog")]:
                try:
                    await asyncio.sleep(0.12)  # 네이버 API 초당 10회 제한
                    res = await client.get(
                        f"https://openapi.naver.com/v1/search/{endpoint}.json",
                        params={"query": keyword, "display": 10, "sort": "date"},
                    )
                    res.raise_for_status()
                    for raw in res.json().get("items", []):
                        title = _strip(raw.get("title", ""))
                        link = raw.get("originallink") or raw.get("link") or ""
                        if not title or not link or link in seen_urls:
                            continue
                        seen_urls.add(link)
                        try:
                            pub_dt = parsedate_to_datetime(raw.get("pubDate", "")).astimezone(KST).isoformat()
                        except Exception:
                            pub_dt = datetime.now(KST).isoformat()
                        results.append({
                            "title": title,
                            "summary": _strip(raw.get("description", "")) or None,
                            "source_url": link,
                            "source_type": source_type,
                            "sentiment": None,
                            "sentiment_score": None,
                            "published_at": pub_dt,
                        })
                except Exception as e:
                    logger.warning(f"뉴스 수집 실패 ({keyword}/{source_type}): {e}")

    # 최신순 50개만 업로드
    results.sort(key=lambda x: x["published_at"] or "", reverse=True)
    results = results[:50]
    logger.info(f"뉴스·블로그 총 {len(results)}건 수집 완료")
    return results


async def upload(yearmonth: str, transactions: list, subscriptions: list, news: list):
    payload = {"yearmonth": yearmonth, "transactions": transactions, "subscriptions": subscriptions, "news": news}
    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(
            f"{RAILWAY_URL}/api/admin/upload",
            json=payload,
            headers={"X-Admin-Token": ADMIN_TOKEN},
        )
        res.raise_for_status()
        return res.json()


async def main(yearmonth: str | None):
    logger.info("=" * 50)
    logger.info("부산 내집마련 데이터 수집 시작")
    logger.info("=" * 50)

    if not MOLIT_KEY:
        logger.error(".env 파일에 MOLIT_API_KEY가 없습니다.")
        sys.exit(1)
    if not ADMIN_TOKEN:
        logger.error(".env 파일에 ADMIN_TOKEN이 없습니다.")
        sys.exit(1)

    if not yearmonth:
        today = date.today()
        yearmonth = f"{today.year}{today.month:02d}"

    logger.info(f"대상 월: {yearmonth}")
    logger.info(f"대상 서버: {RAILWAY_URL}")
    logger.info("")

    logger.info("[1/3] 실거래가 수집 중...")
    transactions = await collect_transactions(yearmonth)

    logger.info("[2/3] 청약·공고 수집 중...")
    subscriptions = await collect_subscriptions()

    logger.info("[3/4] 뉴스·블로그 수집 중...")
    news = await collect_news()

    logger.info("[4/4] Railway에 업로드 중...")
    try:
        result = await upload(yearmonth, transactions, subscriptions, news)
        logger.info(f"업로드 완료: 실거래가 {result['saved']['transactions']}건, 청약 {result['saved']['subscriptions']}건, 뉴스 {result['saved']['news']}건 저장")
    except httpx.HTTPStatusError as e:
        logger.error(f"업로드 실패 HTTP {e.response.status_code}: {e.response.text[:200]}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"업로드 실패: {e}")
        sys.exit(1)

    logger.info("")
    logger.info("완료! 브라우저에서 확인하세요:")
    logger.info(f"  {RAILWAY_URL}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="부산 부동산 데이터 수집 및 Railway 업로드")
    parser.add_argument("--month", help="수집 월 (예: 202504)", default=None)
    args = parser.parse_args()
    asyncio.run(main(args.month))
