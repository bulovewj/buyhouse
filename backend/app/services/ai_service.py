import json
import logging

from anthropic import AsyncAnthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

_ANALYSIS_PROMPT = """다음 부동산 뉴스 제목을 분석해주세요.

제목: {title}

아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
  "summary": "2~3줄 한국어 요약",
  "sentiment": "positive 또는 negative 또는 neutral",
  "sentiment_score": 0.0~1.0
}}"""


async def analyze_news(items: list[dict]) -> list[dict]:
    """뉴스 아이템 리스트를 받아 Claude로 요약·감성분석 후 반환."""
    if not items:
        return items
    if settings.USE_MOCK:
        return items  # 목업 데이터에는 이미 summary/sentiment 포함

    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY 미설정, AI 분석 건너뜀")
        return items

    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    results = []

    for item in items:
        if item.get("summary") and item.get("sentiment"):
            results.append(item)
            continue
        try:
            analyzed = await _analyze_single(client, item)
            results.append(analyzed)
        except Exception as e:
            logger.error(
                f"AI 분석 실패 ({item.get('title', '')[:30]}): "
                f"{type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}"
            )
            results.append(item)

    return results


async def _analyze_single(client: AsyncAnthropic, item: dict) -> dict:
    title = item.get("title", "")
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": _ANALYSIS_PROMPT.format(title=title)}],
    )
    content = message.content[0].text.strip()

    # JSON 블록 추출 (```json ... ``` 래핑 대응)
    if "```" in content:
        content = content.split("```")[-2].lstrip("json").strip()

    parsed = json.loads(content)
    result = dict(item)
    result["summary"] = parsed.get("summary", "")
    result["sentiment"] = parsed.get("sentiment", "neutral")
    result["sentiment_score"] = float(parsed.get("sentiment_score", 0.5))
    return result


async def process_unanalyzed_news() -> int:
    """DB에서 미분석 뉴스(summary 또는 sentiment 없는 행)를 찾아 Claude로 분석 후 저장.
    처리 건수를 반환한다."""
    if settings.USE_MOCK:
        return 0
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY 미설정, process_unanalyzed_news 건너뜀")
        return 0

    from sqlalchemy import or_, select

    from app.core.database import AsyncSessionLocal
    from app.models.models import NewsReaction

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(NewsReaction)
                .where(
                    or_(
                        NewsReaction.summary.is_(None),
                        NewsReaction.sentiment.is_(None),
                    )
                )
                .limit(50)
            )
            rows = result.scalars().all()
        except Exception as e:
            logger.error(
                f"미분석 뉴스 조회 실패: {type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}"
            )
            return 0

        if not rows:
            return 0

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        count = 0

        for row in rows:
            try:
                analyzed = await _analyze_single(client, {"title": row.title})
                row.summary = analyzed["summary"]
                row.sentiment = analyzed["sentiment"]
                row.sentiment_score = analyzed["sentiment_score"]
                count += 1
            except Exception as e:
                logger.error(
                    f"뉴스 AI 분석 실패 (id={row.id}): "
                    f"{type(e).__name__}: {str(e.args[0])[:200] if e.args else ''}"
                )

        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"AI 분석 결과 저장 실패: {type(e).__name__}")
            return 0

        logger.info(f"AI 분석 완료: {count}건")
        return count
