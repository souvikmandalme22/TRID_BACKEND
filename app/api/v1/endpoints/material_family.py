from uuid import UUID
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.base import APIResponse
from app.schemas.material_family import MaterialFamilyCreate, MaterialFamilyUpdate
from app.services.material_family_service import (
    create_family, list_families, get_family,
    update_family, delete_family, seed_default_families,
)

router = APIRouter()


@router.get("/material-families", response_model=APIResponse)
async def list_all_families(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    data = await list_families(active_only, db)
    return APIResponse(data=[f.model_dump() for f in data])


@router.post("/material-families", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_new_family(body: MaterialFamilyCreate, db: AsyncSession = Depends(get_db)):
    data = await create_family(body, db)
    return APIResponse(message="Material family created.", data=data.model_dump())


@router.get("/material-families/{family_id}", response_model=APIResponse)
async def get_one_family(family_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await get_family(family_id, db)
    return APIResponse(data=data.model_dump())


@router.patch("/material-families/{family_id}", response_model=APIResponse)
async def update_one_family(family_id: UUID, body: MaterialFamilyUpdate, db: AsyncSession = Depends(get_db)):
    data = await update_family(family_id, body, db)
    return APIResponse(message="Material family updated.", data=data.model_dump())


@router.delete("/material-families/{family_id}", response_model=APIResponse)
async def delete_one_family(family_id: UUID, db: AsyncSession = Depends(get_db)):
    data = await delete_family(family_id, db)
    return APIResponse(message="Material family deactivated.", data=data)


@router.post("/material-families/seed", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def seed_families(db: AsyncSession = Depends(get_db)):
    await seed_default_families(db)
    return APIResponse(message="Default material families seeded.")
