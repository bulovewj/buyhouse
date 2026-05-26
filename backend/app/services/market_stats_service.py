import logging
from datetime import date

from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_market_stats() -> list:
    """API 라우터용: USE_MOCK=True면 목업, 아니면 DB 집계"""
    if settings.USE_MOCK:
        from app.core.mock_data import MOCK_MARKET_STATS
        return list(MOCK_MARKET_STATS)

    try:
        return await _aggregate_from_db()
    except Exception as e:
        logger.error(f"시세 통계 집계 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")
        return []


async def _aggregate_from_db() -> list:
    """MarketStat 테이블 우선 조회, 없으면 Transaction에서 실시간 집계"""
    from sqlalchemy import func, select
    from app.core.database import AsyncSessionLocal
    from app.models.models import Transaction, MarketStat

    async with AsyncSessionLocal() as db:
        today = date.today()

        # 오늘 저장된 MarketStat이 있으면 바로 반환
        saved_result = await db.execute(
            select(MarketStat).where(MarketStat.stat_date == today)
        )
        saved = saved_result.scalars().all()
        if saved:
            return [
                {
                    "district": r.district,
                    "avg_price": r.avg_price,
                    "avg_jeonse_price": r.avg_jeonse_price,
                    "jeonse_rate": r.jeonse_rate,
                    "unsold_count": r.unsold_count,
                    "transaction_volume": r.transaction_volume,
                    "stat_date": r.stat_date,
                }
                for r in saved
            ]

        # 없으면 Transaction 테이블에서 구별 평균가·거래량 집계
        q = (
            select(
                Transaction.district,
                func.avg(Transaction.price_won).label("avg_price"),
                func.count(Transaction.id).label("transaction_volume"),
            )
            .group_by(Transaction.district)
            .order_by(func.avg(Transaction.price_won).desc())
        )
        rows = (await db.execute(q)).all()

        return [
            {
                "district": row.district,
                "avg_price": int(row.avg_price) if row.avg_price else None,
                "avg_jeonse_price": None,
                "jeonse_rate": None,
                "unsold_count": None,
                "transaction_volume": row.transaction_volume,
                "stat_date": today,
            }
            for row in rows
        ]
