from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.schemas.use_case import UseCaseCreate, UseCaseUpdate
from app.services.use_case_service import (
    create_use_case, list_use_cases, get_use_case,
    update_use_case, delete_use_case, seed_default_use_cases,
)

router = APIRouter()


@router.get("/use-cases", response_model=APIResponse)
async def list_all(active_only: bool = Query(True), db: AsyncSession = Depends(get_db)):
    data = await list_use_cases(active_only, db)
    return APIResponse(data=[u.model_dump() for u in data])


@router.post("/use-cases", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_new(body: UseCaseCreate, db: AsyncSession = Depends(get_db)):
    data = await create_use_case(body, db)
    return APIResponse(message="Use case created.", data=data.model_dump())


@router.get("/use-cases/{use_case_id}", response_model=APIResponse)
async def get_one(use_case_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await get_use_case(use_case_id, db)
    return APIResponse(data=data.model_dump())


@router.patch("/use-cases/{use_case_id}", response_model=APIResponse)
async def update_one(use_case_id: UUID, body: UseCaseUpdate, db: AsyncSession = Depends(get_db)):
    data = await update_use_case(use_case_id, body, db)
    return APIResponse(message="Use case updated.", data=data.model_dump())


@router.delete("/use-cases/{use_case_id}", response_model=APIResponse)
async def delete_one(use_case_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await delete_use_case(use_case_id, db)
    return APIResponse(message="Use case deactivated.", data=data)


@router.post("/use-cases/seed", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def seed(db: AsyncSession = Depends(get_db)):
    await seed_default_use_cases(db)
    return APIResponse(message="Default use cases seeded.")
