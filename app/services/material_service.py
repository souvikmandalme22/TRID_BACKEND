import re
import logging
from uuid import UUID
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.material import Material
from app.models.material_family import MaterialFamily
from app.schemas.material import MaterialCreate, MaterialUpdate, MaterialResponse

logger = logging.getLogger("trid")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")


async def _assert_family_exists(family_id: UUID, db: AsyncSession):
    res = await db.execute(select(MaterialFamily).where(MaterialFamily.id == family_id))
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material family not found.")


async def create_material(data: MaterialCreate, db: AsyncSession) -> MaterialResponse:
    await _assert_family_exists(data.family_id, db)
    slug = _slugify(data.name)
    clash = await db.execute(select(Material).where(Material.slug == slug))
    if clash.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Material '{data.name}' already exists.")

    record = Material(**{**data.model_dump(), "slug": slug, "name": data.name.strip()})
    db.add(record)
    await db.flush()
    await db.refresh(record)
    logger.info(f"Material created: {record.slug}")
    return MaterialResponse.model_validate(record)


async def list_materials(
    db: AsyncSession,
    family_id: Optional[UUID] = None,
    active_only: bool = True,
) -> List[MaterialResponse]:
    query = select(Material).order_by(Material.sort_order, Material.name)
    if active_only:
        query = query.where(Material.is_active == True)
    if family_id:
        query = query.where(Material.family_id == family_id)
    result = await db.execute(query)
    return [MaterialResponse.model_validate(r) for r in result.scalars().all()]


async def get_material(material_id: UUID, db: AsyncSession) -> MaterialResponse:
    result = await db.execute(select(Material).where(Material.id == material_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found.")
    return MaterialResponse.model_validate(record)


async def get_material_by_slug(slug: str, db: AsyncSession) -> MaterialResponse:
    result = await db.execute(select(Material).where(Material.slug == slug))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found.")
    return MaterialResponse.model_validate(record)


async def update_material(material_id: UUID, data: MaterialUpdate, db: AsyncSession) -> MaterialResponse:
    result = await db.execute(select(Material).where(Material.id == material_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found.")

    updates = data.model_dump(exclude_unset=True)

    if "family_id" in updates:
        await _assert_family_exists(updates["family_id"], db)

    if "name" in updates:
        new_slug = _slugify(updates["name"])
        clash = await db.execute(select(Material).where(Material.slug == new_slug, Material.id != material_id))
        if clash.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Material name already taken.")
        record.slug = new_slug

    for key, val in updates.items():
        setattr(record, key, val.strip() if isinstance(val, str) else val)

    await db.flush()
    await db.refresh(record)
    logger.info(f"Material updated: {record.slug}")
    return MaterialResponse.model_validate(record)


async def delete_material(material_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(select(Material).where(Material.id == material_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material not found.")
    record.is_active = False
    await db.flush()
    logger.info(f"Material deactivated: {record.slug}")
    return {"deleted": True, "slug": record.slug}


# family_slug → family UUID helper used by seeder
async def _family_id(slug: str, db: AsyncSession) -> UUID:
    res = await db.execute(select(MaterialFamily).where(MaterialFamily.slug == slug))
    fam = res.scalar_one_or_none()
    if not fam:
        raise RuntimeError(f"Family '{slug}' not found — run material-families seed first.")
    return fam.id


async def seed_default_materials(db: AsyncSession):
    rows = [
        # (name, family_slug, price_per_cc, strength, flex, outdoor, heat, infill, density, tags, desc, order)
        ("PLA",               "plastic",             0.08, "medium", "rigid",    False, False, True,  "normal", "Budget",        "Easy to print, ideal for prototypes and display models",     1),
        ("PETG",              "plastic",             0.12, "medium", "semi-flex", True,  False, True,  "normal", "Best",          "Durable, moisture-resistant, great for functional parts",    2),
        ("ABS",               "plastic",             0.10, "medium", "rigid",    False, True,  True,  "normal", "",              "Tough and heat-resistant, good for enclosures",              3),
        ("Nylon",             "engineering-plastic", 0.18, "high",   "semi-flex", True,  True,  True,  "normal", "Strong",        "High strength and flexibility for demanding applications",   4),
        ("TPU",               "engineering-plastic", 0.20, "medium", "flexible",  True,  False, True,  "light",  "Flexible",      "Rubber-like, perfect for grips, seals and flexible parts",  5),
        ("Standard Resin",    "resin",               0.15, "medium", "rigid",    False, False, False, "normal", "Best",          "Great detail and smooth surface finish",                     6),
        ("Tough Resin",       "resin",               0.22, "high",   "rigid",    False, False, False, "dense",  "Strong",        "Impact-resistant resin for functional prototypes",           7),
        ("Clear Resin",       "resin",               0.25, "medium", "rigid",    False, False, False, "normal", "",              "Transparent resin for optical and display applications",     8),
        ("Flexible Resin",    "resin",               0.28, "low",    "flexible",  False, False, False, "light",  "Flexible",      "Soft and bendable resin for anatomical and wearable models", 9),
        ("High Detail Resin", "resin",               0.30, "medium", "rigid",    False, False, False, "dense",  "Detail",        "Ultra-fine resolution for jewelry and miniatures",           10),
        ("Castable Wax Resin","resin",               0.35, "low",    "rigid",    False, False, False, "normal", "Jewelry",       "Burns out cleanly for lost-wax casting",                    11),
    ]
    for (name, fam_slug, price, strength, flex, outdoor, heat, infill, density, tags, desc, order) in rows:
        slug = _slugify(name)
        exists = await db.execute(select(Material).where(Material.slug == slug))
        if exists.scalar_one_or_none():
            continue
        fid = await _family_id(fam_slug, db)
        db.add(Material(
            family_id=fid, name=name, slug=slug,
            short_description=desc, price_per_cc=price,
            strength_category=strength, flexibility_category=flex,
            outdoor_suitable=outdoor, heat_resistance=heat,
            supports_infill=infill, default_support_density=density,
            tags=tags, sort_order=order,
        ))
    await db.flush()
    logger.info("Default materials seeded.")
