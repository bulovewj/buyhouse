from datetime import datetime, date
from zoneinfo import ZoneInfo

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, Float,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

KST = ZoneInfo("Asia/Seoul")


def now_kst():
    return datetime.now(KST)


class Subscription(Base):
    """청약·공고"""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # 청약|줍줍|행복주택|공공임대
    location: Mapped[str | None] = mapped_column(String(100))
    supply_count: Mapped[int | None] = mapped_column(Integer)
    price_min: Mapped[int | None] = mapped_column(BigInteger)
    price_max: Mapped[int | None] = mapped_column(BigInteger)
    application_start: Mapped[date | None] = mapped_column(Date)
    application_end: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)


class Transaction(Base):
    """실거래가"""
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district: Mapped[str] = mapped_column(String(20))   # 구
    dong: Mapped[str] = mapped_column(String(30))       # 동
    apt_name: Mapped[str] = mapped_column(String(100))
    area_sqm: Mapped[float | None] = mapped_column(Float)
    floor: Mapped[int | None] = mapped_column(Integer)
    price_won: Mapped[int] = mapped_column(BigInteger)
    deal_date: Mapped[date] = mapped_column(Date)
    build_year: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst)


class NewsReaction(Base):
    """뉴스·SNS 반응"""
    __tablename__ = "news_reactions"
    __table_args__ = (UniqueConstraint("source_url", name="uq_news_source_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(500), unique=True)
    source_type: Mapped[str] = mapped_column(String(20))   # 뉴스|블로그
    sentiment: Mapped[str | None] = mapped_column(String(10))      # positive|negative|neutral
    sentiment_score: Mapped[float | None] = mapped_column(Float)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst)


class MarketStat(Base):
    """구별 시세 통계"""
    __tablename__ = "market_stats"
    __table_args__ = (UniqueConstraint("district", "stat_date", name="uq_market_district_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district: Mapped[str] = mapped_column(String(20))
    avg_price: Mapped[int | None] = mapped_column(BigInteger)
    avg_jeonse_price: Mapped[int | None] = mapped_column(BigInteger)
    jeonse_rate: Mapped[float | None] = mapped_column(Float)
    unsold_count: Mapped[int | None] = mapped_column(Integer)
    transaction_volume: Mapped[int | None] = mapped_column(Integer)
    stat_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst)


class NotificationLog(Base):
    """알림 발송 기록"""
    __tablename__ = "notifications_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(10))   # kakao|email
    content: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_kst)
    success: Mapped[bool] = mapped_column(Boolean)


class AppSetting(Base):
    """앱 설정 (항상 id=1 단일 행)"""
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    kakao_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_address: Mapped[str | None] = mapped_column(String(100))
    notify_subscription: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_jjupjjup: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_happy_house: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_public_rental: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_policy: Mapped[bool] = mapped_column(Boolean, default=False)
