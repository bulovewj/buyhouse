import logging
from datetime import date
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

logger = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")
scheduler = AsyncIOScheduler(timezone=KST)


async def daily_full_update():
    """매일 00:00 KST 전체 데이터 갱신"""
    logger.info("전체 데이터 갱신 시작")
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await _update_subscriptions(db)
        await _update_transactions(db)
        await _update_news(db)
        await _update_market_stats(db)

    # 뉴스 AI 분석 (DB 세션 별도)
    try:
        from app.services.ai_service import process_unanalyzed_news
        count = await process_unanalyzed_news()
        if count:
            logger.info(f"AI 분석 완료: {count}건")
    except Exception as e:
        logger.error(f"AI 분석 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")

    logger.info("전체 데이터 갱신 완료")


async def urgent_check():
    """매 6시간 줍줍(무순위) 긴급 체크 (cron: 0 */6 * * *)"""
    logger.info("줍줍 긴급 체크 시작")
    try:
        from app.services.subscription_service import fetch_subscriptions
        items = await fetch_subscriptions(type_filter="줍줍")
        logger.info(f"줍줍 공고 {len(items)}건 확인")

        # 새 줍줍 공고 알림 발송
        if items:
            from app.services.notification_service import notify_new_subscriptions
            await notify_new_subscriptions(items)
    except Exception as e:
        logger.error(f"줍줍 체크 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")


async def _update_subscriptions(db):
    try:
        from app.services.subscription_service import fetch_subscriptions
        from app.models.models import Subscription
        items = await fetch_subscriptions()
        new_items = []
        for item in items:
            if not item.get("source_url"):
                continue
            existing = await db.execute(
                select(Subscription).where(Subscription.source_url == item["source_url"])
            )
            row = existing.scalar_one_or_none()
            if row is None:
                db.add(Subscription(**item))
                new_items.append(item)
        await db.commit()
        logger.info(f"청약 {len(items)}건 upsert 완료 (신규 {len(new_items)}건)")

        # 신규 공고 알림 발송 (DB 세션 별도)
        if new_items:
            from app.services.notification_service import notify_new_subscriptions
            await notify_new_subscriptions(new_items)
    except Exception as e:
        await db.rollback()
        logger.error(f"청약 저장 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")


async def _update_transactions(db):
    try:
        from app.services.transaction_service import fetch_transactions
        from app.models.models import Transaction
        items = await fetch_transactions()
        for item in items:
            db.add(Transaction(**item))
        await db.commit()
        logger.info(f"실거래가 {len(items)}건 저장 완료")
    except Exception as e:
        await db.rollback()
        logger.error(f"실거래가 저장 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")


async def _update_news(db):
    try:
        from app.services.news_service import fetch_news
        from app.models.models import NewsReaction
        items = await fetch_news()
        for item in items:
            existing = await db.execute(
                select(NewsReaction).where(NewsReaction.source_url == item["source_url"])
            )
            if existing.scalar_one_or_none() is None:
                db.add(NewsReaction(**item))
        await db.commit()
        logger.info(f"뉴스 {len(items)}건 upsert 완료")
    except Exception as e:
        await db.rollback()
        logger.error(f"뉴스 저장 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")


async def _update_market_stats(db):
    try:
        from app.services.market_stats_service import fetch_market_stats
        from app.models.models import MarketStat
        items = await fetch_market_stats()
        for item in items:
            existing = await db.execute(
                select(MarketStat).where(
                    MarketStat.district == item["district"],
                    MarketStat.stat_date == item["stat_date"],
                )
            )
            row = existing.scalar_one_or_none()
            if row is None:
                db.add(MarketStat(**item))
            else:
                for k, v in item.items():
                    setattr(row, k, v)
        await db.commit()
        logger.info(f"시세통계 {len(items)}개 구 upsert 완료")
    except Exception as e:
        await db.rollback()
        logger.error(f"시세통계 저장 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")


# 스케줄 등록
scheduler.add_job(daily_full_update, CronTrigger(hour=0, minute=0, timezone=KST), id="daily_full_update")
scheduler.add_job(urgent_check, CronTrigger(hour="0,6,12,18", minute=0, timezone=KST), id="urgent_check")
