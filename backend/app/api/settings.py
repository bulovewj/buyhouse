from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db

router = APIRouter(tags=["settings"])


class SettingsResponse(BaseModel):
    id: int = 1
    kakao_enabled: bool
    email_enabled: bool
    email_address: Optional[str] = None
    notify_subscription: bool
    notify_jjupjjup: bool
    notify_happy_house: bool
    notify_public_rental: bool
    notify_policy: bool

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    kakao_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    email_address: Optional[str] = None
    notify_subscription: Optional[bool] = None
    notify_jjupjjup: Optional[bool] = None
    notify_happy_house: Optional[bool] = None
    notify_public_rental: Optional[bool] = None
    notify_policy: Optional[bool] = None


async def _get_or_create_settings(db: AsyncSession):
    from app.models.models import AppSetting
    result = await db.execute(select(AppSetting).where(AppSetting.id == 1))
    row = result.scalar_one_or_none()
    if row is None:
        row = AppSetting(id=1)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await _get_or_create_settings(db)


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    row = await _get_or_create_settings(db)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return row
