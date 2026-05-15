import re
import logging
from uuid import UUID
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.material_family import MaterialFamily
from app.schemas.material_family import MaterialFamilyCreate, MaterialFamilyUpdate, MaterialFamilyResponse

logger = logging.getLogger("trid")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")


async def create_family(data: MaterialFamilyCreate, db: AsyncSession) -> MaterialFamilyResponse:
    slug = _slugify(data.name)
    clash = await db.execute(select(MaterialFamily).where(MaterialFamily.slug == slug))
    if clash.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Material family '{data.name}' already exists.")

    record = MaterialFamily(
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
    logger.info(f"MaterialFamily created: {record.slug}")
    return MaterialFamilyResponse.model_validate(record)


async def list_families(active_only: bool, db: AsyncSession) -> List[MaterialFamilyResponse]:
    query = select(MaterialFamily).order_by(MaterialFamily.sort_order, MaterialFamily.name)
    if active_only:
        query = query.where(MaterialFamily.is_active == True)
    result = await db.execute(query)
    return [MaterialFamilyResponse.model_validate(r) for r in result.scalars().all()]


async def get_family(family_id: UUID, db: AsyncSession) -> MaterialFamilyResponse:
    result = await db.execute(select(MaterialFamily).where(MaterialFamily.id == family_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material family not found.")
    return MaterialFamilyResponse.model_validate(record)


async def update_family(family_id: UUID, data: MaterialFamilyUpdate, db: AsyncSession) -> MaterialFamilyResponse:
    result = await db.execute(select(MaterialFamily).where(MaterialFamily.id == family_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material family not found.")

    updates = data.model_dump(exclude_unset=True)
    if "name" in updates:
        new_slug = _slugify(updates["name"])
        clash = await db.execute(select(MaterialFamily).where(MaterialFamily.slug == new_slug, MaterialFamily.id != family_id))
        if clash.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Material family name already taken.")
        record.slug = new_slug

    for key, val in updates.items():
        setattr(record, key, val.strip() if isinstance(val, str) else val)

    await db.flush()
    await db.refresh(record)
    logger.info(f"MaterialFamily updated: {record.slug}")
    return MaterialFamilyResponse.model_validate(record)


async def delete_family(family_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(select(MaterialFamily).where(MaterialFamily.id == family_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material family not found.")
    record.is_active = False
    await db.flush()
    logger.info(f"MaterialFamily deactivated: {record.slug}")
    return {"deleted": True, "slug": record.slug}


async def seed_default_families(db: AsyncSession):
    defaults = [
        ("Plastic",             "icon-plastic",              "Standard plastics for general use prints",              1),
        ("Engineering Plastic", "icon-engineering-plastic",  "High-strength plastics for functional applications",    2),
        ("Resin",               "icon-resin",                "High-detail resin for fine and intricate models",       3),
        ("Industrial",          "icon-industrial-material",  "Industrial-grade materials for heavy-duty applications",4),
        ("Metal",               "icon-metal",                "Metal materials for structural and premium parts",       5),
    ]
    for name, icon, desc, order in defaults:
        slug = _slugify(name)
        existing = await db.execute(select(MaterialFamily).where(MaterialFamily.slug == slug))
        if not existing.scalar_one_or_none():
            db.add(MaterialFamily(name=name, slug=slug, icon_ref=icon, description=desc, sort_order=order))
    await db.flush()
    logger.info("Default material families seeded.")
