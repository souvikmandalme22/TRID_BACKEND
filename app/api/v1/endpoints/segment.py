from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.schemas.segment import SegmentCreate, SegmentUpdate
from app.services.segment_service import (
    create_segment, list_segments, get_segment,
    update_segment, delete_segment, seed_default_segments,
)

router = APIRouter()


@router.get("/segments", response_model=APIResponse)
async def list_all_segments(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    data = await list_segments(active_only, db)
    return APIResponse(data=[s.model_dump() for s in data])


@router.post("/segments", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_new_segment(body: SegmentCreate, db: AsyncSession = Depends(get_db)):
    data = await create_segment(body, db)
    return APIResponse(message="Segment created.", data=data.model_dump())


@router.get("/segments/{segment_id}", response_model=APIResponse)
async def get_one_segment(segment_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await get_segment(segment_id, db)
    return APIResponse(data=data.model_dump())


@router.patch("/segments/{segment_id}", response_model=APIResponse)
async def update_one_segment(segment_id: UUID, body: SegmentUpdate, db: AsyncSession = Depends(get_db)):
    data = await update_segment(segment_id, body, db)
    return APIResponse(message="Segment updated.", data=data.model_dump())


@router.delete("/segments/{segment_id}", response_model=APIResponse)
async def delete_one_segment(segment_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await delete_segment(segment_id, db)
    return APIResponse(message="Segment deactivated.", data=data)


@router.post("/segments/seed", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def seed_segments(db: AsyncSession = Depends(get_db)):
    await seed_default_segments(db)
    return APIResponse(message="Default segments seeded.")
