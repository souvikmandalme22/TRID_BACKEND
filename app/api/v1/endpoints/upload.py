from fastapi import APIRouter, UploadFile, File, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.upload import UploadResponse
from app.schemas.base import APIResponse
from app.services.upload_service import save_upload, get_model_by_id

router = APIRouter()


@router.post("/upload", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def upload_model(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    record = await save_upload(file, db)
    return APIResponse(
        message="Model uploaded successfully.",
        data=UploadResponse.model_validate(record).model_dump(),
    )


@router.get("/upload/{model_id}", response_model=APIResponse)
async def get_upload_status(
    model_id: str,
    db: AsyncSession = Depends(get_db),
):
    record = await get_model_by_id(model_id, db)
    return APIResponse(
        data=UploadResponse.model_validate(record).model_dump()
    )
