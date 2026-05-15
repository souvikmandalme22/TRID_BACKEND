import re
import logging
from uuid import UUID
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.use_case import UseCase
from app.schemas.use_case import UseCaseCreate, UseCaseUpdate, UseCaseResponse

logger = logging.getLogger("trid")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")


async def create_use_case(data: UseCaseCreate, db: AsyncSession) -> UseCaseResponse:
    slug = _slugify(data.name)
    clash = await db.execute(select(UseCase).where(UseCase.slug == slug))
    if clash.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Use case '{data.name}' already exists.")

    record = UseCase(**{**data.model_dump(), "slug": slug, "name": data.name.strip()})
    db.add(record)
    await db.flush()
    await db.refresh(record)
    logger.info(f"UseCase created: {record.slug}")
    return UseCaseResponse.model_validate(record)


async def list_use_cases(active_only: bool, db: AsyncSession) -> List[UseCaseResponse]:
    query = select(UseCase).order_by(UseCase.sort_order, UseCase.name)
    if active_only:
        query = query.where(UseCase.is_active == True)
    result = await db.execute(query)
    return [UseCaseResponse.model_validate(r) for r in result.scalars().all()]


async def get_use_case(use_case_id: UUID, db: AsyncSession) -> UseCaseResponse:
    result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found.")
    return UseCaseResponse.model_validate(record)


async def update_use_case(use_case_id: UUID, data: UseCaseUpdate, db: AsyncSession) -> UseCaseResponse:
    result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found.")

    updates = data.model_dump(exclude_unset=True)
    if "name" in updates:
        new_slug = _slugify(updates["name"])
        clash = await db.execute(select(UseCase).where(UseCase.slug == new_slug, UseCase.id != use_case_id))
        if clash.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Use case name already taken.")
        record.slug = new_slug

    for key, val in updates.items():
        setattr(record, key, val.strip() if isinstance(val, str) else val)

    await db.flush()
    await db.refresh(record)
    logger.info(f"UseCase updated: {record.slug}")
    return UseCaseResponse.model_validate(record)


async def delete_use_case(use_case_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found.")
    record.is_active = False
    await db.flush()
    logger.info(f"UseCase deactivated: {record.slug}")
    return {"deleted": True, "slug": record.slug}


async def seed_default_use_cases(db: AsyncSession):
    defaults = [
        ("Showpiece",     "showpiece",    "Decorative display models, not subject to mechanical stress",   "low",    "low",    1),
        ("Fit / Assembly","fit-assembly", "Parts that must fit together with tolerance and precision",     "medium", "medium", 2),
        ("Daily Use",     "daily-use",    "Functional items used regularly under normal conditions",       "high",   "high",   3),
        ("Heavy-Duty",    "heavy-duty",   "Structural or load-bearing parts in demanding environments",   "extreme","ultra",  4),
    ]
    for name, slug, desc, durability, strength, order in defaults:
        exists = await db.execute(select(UseCase).where(UseCase.slug == slug))
        if not exists.scalar_one_or_none():
            db.add(UseCase(
                name=name, slug=slug, description=desc,
                durability_level=durability, recommended_strength=strength,
                sort_order=order,
            ))
    await db.flush()
    logger.info("Default use cases seeded.")
