import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_market_stats() -> list:
    if settings.USE_MOCK:
        from app.core.mock_data import MOCK_MARKET_STATS
        return MOCK_MARKET_STATS

    try:
        return await _aggregate_from_db()
    except Exception as e:
        logger.error(f"시세 통계 집계 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}")
        return []


async def _aggregate_from_db() -> list:
    # transactions 테이블에서 구별 평균가 집계
    # jeonse_rate = avg_jeonse_price / avg_price
    # TODO: AsyncSession으로 SQLAlchemy 집계 쿼리 실행
    return []
