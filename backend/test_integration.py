"""통합 테스트 스크립트 — 실행 중인 서버 대상 전체 엔드포인트 검증.

사용법:
    python3 test_integration.py [BASE_URL]

    BASE_URL 기본값: http://localhost:8000
    Railway 배포 확인 예시: python3 test_integration.py https://your-app.up.railway.app
"""

import asyncio
import sys
from typing import Any

import httpx

BASE_URL = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"

PASS = "✅"
FAIL = "❌"
SKIP = "⏭ "

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    icon = PASS if condition else FAIL
    results.append((name, condition, detail))
    print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))


async def run_tests(client: httpx.AsyncClient) -> None:
    print(f"\n🔍 테스트 대상: {BASE_URL}\n")

    # ── 헬스체크 ──────────────────────────────────────────
    print("[ 헬스체크 ]")
    try:
        r = await client.get("/healthz")
        check("GET /healthz → 200", r.status_code == 200)
        check("status=ok", r.json().get("status") == "ok")
    except Exception as e:
        check("GET /healthz", False, str(e))
        print("  서버에 연결할 수 없습니다. 종료합니다.")
        return

    # ── 청약·공고 ─────────────────────────────────────────
    print("\n[ 청약·공고 ]")
    r = await client.get("/api/subscriptions", params={"page": 1, "limit": 5})
    check("GET /api/subscriptions → 200", r.status_code == 200)
    d = r.json()
    check("total 필드 존재", "total" in d, f"total={d.get('total')}")
    check("items 리스트", isinstance(d.get("items"), list))
    if d.get("items"):
        item = d["items"][0]
        check("item.title 존재", "title" in item)
        check("item.type 존재", "type" in item)

    r2 = await client.get("/api/subscriptions", params={"type": "줍줍"})
    check("GET /api/subscriptions?type=줍줍 → 200", r2.status_code == 200)
    check("줍줍 필터 동작", all(i["type"] == "줍줍" for i in r2.json().get("items", [])))

    # ── 실거래가 ──────────────────────────────────────────
    print("\n[ 실거래가 ]")
    r = await client.get("/api/transactions", params={"page": 1, "limit": 5})
    check("GET /api/transactions → 200", r.status_code == 200)
    d = r.json()
    check("total ≥ 0", (d.get("total") or 0) >= 0, f"total={d.get('total')}")
    if d.get("items"):
        item = d["items"][0]
        check("item.price_won 존재", "price_won" in item)
        check("price_won 단위 (원, 1억 이상)", (item.get("price_won") or 0) >= 100_000_000)

    r2 = await client.get("/api/transactions", params={"district": "해운대구"})
    check("GET /api/transactions?district=해운대구 → 200", r2.status_code == 200)

    # ── 뉴스 ──────────────────────────────────────────────
    print("\n[ 뉴스 ]")
    r = await client.get("/api/news", params={"limit": 5})
    check("GET /api/news → 200", r.status_code == 200)
    d = r.json()
    check("total ≥ 0", (d.get("total") or 0) >= 0, f"total={d.get('total')}")
    if d.get("items"):
        item = d["items"][0]
        check("item.title 존재", "title" in item)
        check("item.source_url 존재", "source_url" in item)
        check("sentiment 값 유효", item.get("sentiment") in (None, "positive", "negative", "neutral"))

    r2 = await client.get("/api/news", params={"sentiment": "positive"})
    check("GET /api/news?sentiment=positive → 200", r2.status_code == 200)
    check("감성 필터 동작", all(i["sentiment"] == "positive" for i in r2.json().get("items", [])))

    r3 = await client.get("/api/policy-news")
    check("GET /api/policy-news → 200", r3.status_code == 200)

    # ── 시세분석 ──────────────────────────────────────────
    print("\n[ 시세분석 ]")
    r = await client.get("/api/market-stats")
    check("GET /api/market-stats → 200", r.status_code == 200)
    d = r.json()
    check("stat_date 존재", "stat_date" in d)
    check("districts 리스트", isinstance(d.get("districts"), list))
    check("16개 구 데이터", len(d.get("districts", [])) >= 16, f"{len(d.get('districts', []))}개 구")
    if d.get("districts"):
        dist = d["districts"][0]
        check("avg_price 원 단위 (1억 이상)", (dist.get("avg_price") or 0) >= 100_000_000)

    # ── 설정 ──────────────────────────────────────────────
    print("\n[ 설정 ]")
    r = await client.get("/api/settings")
    check("GET /api/settings → 200", r.status_code == 200)
    d = r.json()
    check("id=1", d.get("id") == 1)
    for field in ["kakao_enabled", "email_enabled", "notify_subscription"]:
        check(f"  {field} 존재", field in d)

    update_payload = {"notify_policy": True}
    r2 = await client.put("/api/settings", json=update_payload)
    check("PUT /api/settings → 200", r2.status_code == 200)
    check("PUT 반영 확인", r2.json().get("notify_policy") is True)

    # ── 알림 ──────────────────────────────────────────────
    print("\n[ 알림 ]")
    r = await client.post("/api/notifications/test", json={"type": "kakao"})
    check("POST /api/notifications/test → 200", r.status_code == 200)
    check("success 필드", "success" in r.json())

    r2 = await client.post("/api/notifications/run-ai")
    check("POST /api/notifications/run-ai → 200", r2.status_code == 200)
    check("processed_count 필드", "processed_count" in r2.json())

    # ── 대출계산기 ────────────────────────────────────────
    print("\n[ 대출계산기 ]")
    payload = {
        "house_price": 50000,
        "own_fund": 15000,
        "annual_income": 5000,
        "loan_years": 30,
        "interest_rate": 3.5,
        "loan_type": "일반",
    }
    r = await client.post("/api/calculator/calculate", json=payload)
    check("POST /api/calculator/calculate → 200", r.status_code == 200)
    d = r.json()
    check("loan_needed = 35000", d.get("loan_needed") == 35000, f"실제: {d.get('loan_needed')}")
    check("ltv_limit = 35000 (70%)", d.get("ltv_limit") == 35000, f"실제: {d.get('ltv_limit')}")
    check("ltv_ok = True", d.get("ltv_ok") is True)
    check("monthly_payment > 0", (d.get("monthly_payment") or 0) > 0)
    check("feasible 필드", "feasible" in d)

    r2 = await client.post("/api/calculator/calculate", json={**payload, "loan_type": "생애최초"})
    check("생애최초 LTV 80% 적용", r2.json().get("ltv_limit") == 40000)

    # ── 어드민 인증 ────────────────────────────────────────
    print("\n[ 어드민 인증 ]")
    r = await client.post("/api/admin/run-update")
    # 헤더 누락 → FastAPI 422 (검증 오류), 잘못된 헤더 → 403. 둘 다 인증 거부로 간주
    check("어드민 토큰 없이 → 4xx", r.status_code in (403, 422), f"실제: {r.status_code}")

    r2 = await client.post("/api/admin/run-update", headers={"X-Admin-Token": "wrong-token"})
    check("잘못된 토큰 → 403", r2.status_code == 403)


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15) as client:
        await run_tests(client)

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    print(f"\n{'='*50}")
    print(f"결과: {passed}/{total} 통과" + (f" | {failed}건 실패" if failed else " — 전체 통과 🎉"))
    print("=" * 50)

    if failed:
        print("\n실패 항목:")
        for name, ok, detail in results:
            if not ok:
                print(f"  {FAIL} {name}" + (f" — {detail}" if detail else ""))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
