from fastapi import APIRouter, Depends, HTTPException, Header

from app.core.config import settings

router = APIRouter(tags=["admin"])


async def verify_admin(x_admin_token: str = Header(...)):
    if x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/admin/run-update", dependencies=[Depends(verify_admin)])
async def run_update():
    """전체 데이터 업데이트 즉시 실행 (테스트용)"""
    from app.scheduler.tasks import daily_full_update
    await daily_full_update()
    return {"status": "ok", "message": "전체 업데이트 완료"}


@router.post("/admin/run-urgent", dependencies=[Depends(verify_admin)])
async def run_urgent():
    """줍줍 긴급 체크 즉시 실행"""
    from app.scheduler.tasks import urgent_check
    await urgent_check()
    return {"status": "ok", "message": "줍줍 긴급 체크 완료"}
