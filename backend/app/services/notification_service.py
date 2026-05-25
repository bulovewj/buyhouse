import json
import logging
from email.message import EmailMessage

import aiosmtplib
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_KAKAO_MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


async def send_kakao(message: str) -> bool:
    """카카오 나에게 보내기 API로 텍스트 알림 발송."""
    if settings.USE_MOCK:
        logger.info(f"[목업] 카카오 알림: {message[:80]}")
        return True

    if not settings.KAKAO_ACCESS_TOKEN:
        logger.warning("KAKAO_ACCESS_TOKEN 미설정, 카카오 알림 건너뜀")
        return False

    try:
        headers = {"Authorization": f"Bearer {settings.KAKAO_ACCESS_TOKEN}"}
        payload = {
            "template_object": json.dumps(
                {
                    "object_type": "text",
                    "text": message,
                    "link": {"web_url": "", "mobile_web_url": ""},
                },
                ensure_ascii=False,
            )
        }
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(_KAKAO_MEMO_URL, headers=headers, data=payload)
            res.raise_for_status()
        logger.info("카카오 알림 발송 성공")
        return True
    except httpx.HTTPStatusError as e:
        logger.error(f"카카오 알림 HTTP 오류 {e.response.status_code}: {type(e).__name__}")
        return False
    except Exception as e:
        logger.error(
            f"카카오 알림 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}"
        )
        return False


async def send_email(subject: str, body: str, to: str) -> bool:
    """Gmail SMTP(TLS 465)로 이메일 발송."""
    if settings.USE_MOCK:
        logger.info(f"[목업] 이메일 발송: '{subject}' → {to}")
        return True

    if not settings.GMAIL_USER or not settings.GMAIL_APP_PASSWORD:
        logger.warning("Gmail 설정 미완료, 이메일 발송 건너뜀")
        return False

    try:
        msg = EmailMessage()
        msg["From"] = settings.GMAIL_USER
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)

        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=465,
            use_tls=True,
            username=settings.GMAIL_USER,
            password=settings.GMAIL_APP_PASSWORD,
        )
        logger.info(f"이메일 발송 성공: {to}")
        return True
    except Exception as e:
        logger.error(
            f"이메일 발송 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}"
        )
        return False


async def notify_new_subscriptions(new_items: list[dict]) -> None:
    """새 청약 공고 발생 시 설정된 채널로 알림을 발송하고 NotificationLog에 기록한다."""
    if not new_items:
        return

    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.models import AppSetting, NotificationLog

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(AppSetting).where(AppSetting.id == 1))
            app_setting = result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"알림 설정 조회 실패: {type(e).__name__}")
            return

        if not app_setting:
            return

        # 항목별 알림 설정 필터
        type_filter = {
            "subscription": app_setting.notify_subscription,
            "jjupjjup": app_setting.notify_jjupjjup,
            "happy_house": app_setting.notify_happy_house,
            "public_rental": app_setting.notify_public_rental,
        }
        filtered = [i for i in new_items if type_filter.get(i.get("type"), True)]
        if not filtered:
            return

        # 알림 메시지 구성
        lines = ["[부산 내집마련] 신규 청약·공고 알림\n"]
        for item in filtered[:5]:  # 최대 5개
            lines.append(f"▶ {item.get('title', '(제목 없음)')}")
            lines.append(f"   위치: {item.get('location', '-')}")
            lines.append(f"   마감: {item.get('application_end', '-')}\n")
        message = "\n".join(lines)

        # 카카오 발송
        if app_setting.kakao_enabled:
            success = await send_kakao(message)
            db.add(NotificationLog(type="kakao", content=message[:500], success=success))

        # 이메일 발송
        if app_setting.email_enabled and app_setting.email_address:
            success = await send_email(
                subject="[부산 내집마련] 신규 청약·공고 알림",
                body=message,
                to=app_setting.email_address,
            )
            db.add(NotificationLog(type="email", content=message[:500], success=success))

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"알림 로그 저장 실패: {type(e).__name__}")
