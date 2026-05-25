from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["notifications"])


class TestRequest(BaseModel):
    type: str  # kakao|email|both


class TestResponse(BaseModel):
    success: bool
    message: str


class AiRunResponse(BaseModel):
    processed_count: int


@router.post("/notifications/test", response_model=TestResponse)
async def test_notification(body: TestRequest):
    from app.services.notification_service import send_email, send_kakao
    from app.core.config import settings

    test_msg = "[부산 내집마련] 알림 테스트 메시지입니다."
    results = []

    if body.type in ("kakao", "both"):
        ok = await send_kakao(test_msg)
        results.append(f"카카오: {'성공' if ok else '실패'}")

    if body.type in ("email", "both"):
        if settings.GMAIL_USER:
            ok = await send_email(
                subject="[부산 내집마련] 알림 테스트",
                body=test_msg,
                to=settings.GMAIL_USER,
            )
            results.append(f"이메일: {'성공' if ok else '실패'}")
        else:
            results.append("이메일: Gmail 미설정")

    if not results:
        return TestResponse(success=False, message=f"알 수 없는 type: {body.type}")

    success = all("성공" in r or "목업" in r or "Mock" in r for r in results)
    return TestResponse(success=True, message=" / ".join(results))


@router.post("/notifications/run-ai", response_model=AiRunResponse)
async def run_ai_analysis():
    from app.services.ai_service import process_unanalyzed_news

    count = await process_unanalyzed_news()
    return AiRunResponse(processed_count=count)
