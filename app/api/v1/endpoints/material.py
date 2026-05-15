from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.schemas.material import MaterialCreate, MaterialUpdate
from app.services.material_service import (
    create_material, list_materials, get_material,
    get_material_by_slug, update_material,
    delete_material, seed_default_materials,
)

router = APIRouter()


@router.get("/materials", response_model=APIResponse)
async def list_all_materials(
    family_id: Optional[UUID] = Query(None),
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    data = await list_materials(db, family_id=family_id, active_only=active_only)
    return APIResponse(data=[m.model_dump() for m in data])


@router.post("/materials", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_new_material(body: MaterialCreate, db: AsyncSession = Depends(get_db)):
    data = await create_material(body, db)
    return APIResponse(message="Material created.", data=data.model_dump())


@router.get("/materials/by-slug/{slug}", response_model=APIResponse)
async def get_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    data = await get_material_by_slug(slug, db)
    return APIResponse(data=data.model_dump())


@router.get("/materials/{material_id}", response_model=APIResponse)
async def get_one_material(material_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await get_material(material_id, db)
    return APIResponse(data=data.model_dump())


@router.patch("/materials/{material_id}", response_model=APIResponse)
async def update_one_material(material_id: UUID, body: MaterialUpdate, db: AsyncSession = Depends(get_db)):
    data = await update_material(material_id, body, db)
    return APIResponse(message="Material updated.", data=data.model_dump())


@router.delete("/materials/{material_id}", response_model=APIResponse)
async def delete_one_material(material_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await delete_material(material_id, db)
    return APIResponse(message="Material deactivated.", data=data)


@router.post("/materials/seed", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def seed_materials(db: AsyncSession = Depends(get_db)):
    await seed_default_materials(db)
    return APIResponse(message="Default materials seeded.")
