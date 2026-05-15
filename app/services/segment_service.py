import re
import logging
from uuid import UUID
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.segment import Segment
from app.schemas.segment import SegmentCreate, SegmentUpdate, SegmentResponse

logger = logging.getLogger("trid")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")


async def create_segment(data: SegmentCreate, db: AsyncSession) -> SegmentResponse:
    slug = _slugify(data.name)

    existing = await db.execute(select(Segment).where(Segment.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Segment '{data.name}' already exists.")

    record = Segment(
        name=data.name.strip(),
        slug=slug,
        icon_ref=data.icon_ref,
        description=data.description,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    logger.info(f"Segment created: {record.slug}")
    return SegmentResponse.model_validate(record)


async def list_segments(active_only: bool, db: AsyncSession) -> List[SegmentResponse]:
    query = select(Segment).order_by(Segment.sort_order, Segment.name)
    if active_only:
        query = query.where(Segment.is_active == True)
    result = await db.execute(query)
    return [SegmentResponse.model_validate(r) for r in result.scalars().all()]


async def get_segment(segment_id: UUID, db: AsyncSession) -> SegmentResponse:
    result = await db.execute(select(Segment).where(Segment.id == segment_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found.")
    return SegmentResponse.model_validate(record)


async def update_segment(segment_id: UUID, data: SegmentUpdate, db: AsyncSession) -> SegmentResponse:
    result = await db.execute(select(Segment).where(Segment.id == segment_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found.")

    updates = data.model_dump(exclude_unset=True)
    if "name" in updates:
        new_slug = _slugify(updates["name"])
        clash = await db.execute(select(Segment).where(Segment.slug == new_slug, Segment.id != segment_id))
        if clash.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Segment name already taken.")
        record.slug = new_slug

    for key, val in updates.items():
        setattr(record, key, val.strip() if isinstance(val, str) else val)

    await db.flush()
    await db.refresh(record)
    logger.info(f"Segment updated: {record.slug}")
    return SegmentResponse.model_validate(record)


async def delete_segment(segment_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(select(Segment).where(Segment.id == segment_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment not found.")
    record.is_active = False
    await db.flush()
    logger.info(f"Segment deactivated: {record.slug}")
    return {"deleted": True, "slug": record.slug}


async def seed_default_segments(db: AsyncSession):
    defaults = [
        ("Engineering",   "icon-engineering",   "Functional parts, prototypes, mechanical components", 1),
        ("Automotive",    "icon-automotive",     "Car parts, brackets, custom automotive components",  2),
        ("Medical",       "icon-medical",        "Medical devices, prosthetics, surgical tools",       3),
        ("Jewelry",       "icon-jewelry",        "Rings, pendants, intricate decorative pieces",       4),
        ("Industrial",    "icon-industrial",     "Heavy-duty industrial parts and tooling",            5),
        ("Consumer",      "icon-consumer",       "Everyday consumer products and gadgets",             6),
        ("Robotics",      "icon-robotics",       "Robot parts, mounts, servo housings",               7),
        ("Architecture",  "icon-architecture",   "Architectural models and structural prototypes",     8),
    ]
    for name, icon, desc, order in defaults:
        slug = _slugify(name)
        existing = await db.execute(select(Segment).where(Segment.slug == slug))
        if not existing.scalar_one_or_none():
            db.add(Segment(name=name, slug=slug, icon_ref=icon, description=desc, sort_order=order))
    await db.flush()
    logger.info("Default segments seeded.")
