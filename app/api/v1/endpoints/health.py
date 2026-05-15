from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db.session import get_db
from app.schemas.base import APIResponse
from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=APIResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return APIResponse(
        message="TRID backend is healthy",
        data={"app": settings.APP_NAME, "env": settings.APP_ENV, "db": "connected"},
    )
