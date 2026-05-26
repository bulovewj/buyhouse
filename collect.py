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
import sys
import xml.etree.ElementTree as ET
from datetime import date

import httpx
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

MOLIT_KEY      = os.getenv("MOLIT_API_KEY", "")
APPLYHOME_KEY  = os.getenv("APPLYHOME_API_KEY", "")
LH_KEY         = os.getenv("LH_API_KEY", "")
RAILWAY_URL    = os.getenv("RAILWAY_URL", "https://buyhouse-production.up.railway.app")
ADMIN_TOKEN    = os.getenv("ADMIN_TOKEN", "")

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

    # 청약홈
    try:
        async with httpx.AsyncClient(timeout=30, headers=UA) as client:
            res = await client.get(
                "https://apis.data.go.kr/B552555/APTInfoService/getAPTLttotPblancMdList",
                params={"serviceKey": APPLYHOME_KEY, "sidoNm": "부산광역시",
                        "numOfRows": 100, "pageNo": 1},
            )
            res.raise_for_status()
            root = ET.fromstring(res.text)

            def xtext(item, *tags):
                for tag in tags:
                    v = item.findtext(tag)
                    if v and v.strip():
                        return v.strip()
                return ""

            before = len(results)
            for item in root.findall(".//item"):
                t = lambda *tags: xtext(item, *tags)  # noqa: E731
                if "부산" not in t("SIDO_NM", "sidoNm"):
                    continue
                title = t("HOUSE_NM", "housNm")
                if not title:
                    continue
                house_secd = t("HOUSE_SECD_NM", "houseSecd")
                sub_type = "줍줍" if "무순위" in house_secd else "청약"
                manage_no = t("HOUSE_MANAGE_NO", "pnahouseManageNo")
                supply_count = None
                try:
                    sc = t("TOT_SUPLY_HSHLDCO", "totSuplyHshldco")
                    if sc:
                        supply_count = int(sc.replace(",", ""))
                except ValueError:
                    pass
                results.append({
                    "title": title, "type": sub_type,
                    "location": f"부산 {t('SGG_NM','sggNm')} {t('EML_NM','emdNm')}".strip(),
                    "supply_count": supply_count, "price_min": None, "price_max": None,
                    "application_start": _parse_date(t("RCEPT_BGNDE", "rcptBgnDe")),
                    "application_end":   _parse_date(t("RCEPT_ENDDE", "rcptEndDe")),
                    "source_url": (
                        f"https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancListForm.do"
                        f"?houseManageNo={manage_no}" if manage_no else None
                    ),
                    "is_notified": False,
                })
            logger.info(f"청약홈: {len(results) - before}건 수집")
    except httpx.HTTPStatusError as e:
        logger.warning(f"청약홈 HTTP {e.response.status_code} — 건너뜀")
    except Exception as e:
        logger.warning(f"청약홈 수집 실패: {e}")

    # LH
    lh_before = len(results)
    try:
        async with httpx.AsyncClient(timeout=30, headers=UA) as client:
            res = await client.get(
                "https://apis.data.go.kr/B552555/lhNoticeDtlInfo1/lhNoticeDtlInfo1",
                params={"serviceKey": LH_KEY, "PG_SZ": 100, "PAGE": 1, "CNP_CD": "26"},
            )
            res.raise_for_status()
            data = res.json()
            raw_items = data.get("dsList") or data.get("data") or (data if isinstance(data, list) else [])
            for raw in raw_items:
                title = raw.get("AIS_TP_NM") or raw.get("PAN_NM") or ""
                if not title:
                    continue
                sido = raw.get("CNP_CD_NM") or ""
                if sido and "부산" not in sido:
                    continue
                ais_tp = raw.get("AIS_TP_CD_NM") or ""
                pan_id = raw.get("PAN_ID") or ""
                results.append({
                    "title": title,
                    "type": "행복주택" if "행복" in ais_tp else "공공임대",
                    "location": f"부산 {raw.get('SGG_NM', '')}".strip(),
                    "supply_count": None, "price_min": None, "price_max": None,
                    "application_start": _parse_date(str(raw.get("PAN_SS") or "")),
                    "application_end":   _parse_date(str(raw.get("PAN_DE") or "")),
                    "source_url": (
                        f"https://apply.lh.or.kr/lhapply/apply/wt/wrtanc/selectWtanNoList.do?sc={pan_id}"
                        if pan_id else None
                    ),
                    "is_notified": False,
                })
        logger.info(f"LH: {len(results) - lh_before}건 수집")
    except httpx.HTTPStatusError as e:
        logger.warning(f"LH HTTP {e.response.status_code} — 건너뜀")
    except Exception as e:
        logger.warning(f"LH 수집 실패: {e}")

    logger.info(f"청약·공고 총 {len(results)}건 수집 완료")
    return results


async def upload(yearmonth: str, transactions: list, subscriptions: list):
    payload = {"yearmonth": yearmonth, "transactions": transactions, "subscriptions": subscriptions}
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

    logger.info("[3/3] Railway에 업로드 중...")
    try:
        result = await upload(yearmonth, transactions, subscriptions)
        logger.info(f"업로드 완료: 실거래가 {result['saved']['transactions']}건, 청약 {result['saved']['subscriptions']}건 저장")
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
