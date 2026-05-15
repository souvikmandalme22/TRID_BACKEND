import uuid
import os
import aiofiles
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.upload import UploadedModel, UploadStatus, FileType
from app.utils.file_validator import (
    validate_extension,
    validate_file_size,
    validate_geometry,
)
import logging

logger = logging.getLogger("trid")

STORAGE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "models"
)

EXT_TO_FILETYPE = {
    ".stl": FileType.stl,
    ".obj": FileType.obj,
    ".step": FileType.step,
    ".stp": FileType.stp,
}


def _ensure_storage():
    os.makedirs(STORAGE_DIR, exist_ok=True)


async def save_upload(file: UploadFile, db: AsyncSession) -> UploadedModel:
    _ensure_storage()

    ext = validate_extension(file.filename)
    contents = await file.read()
    file_size = len(contents)

    validate_file_size(file_size)

    if not validate_geometry(contents, ext):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Corrupted or invalid 3D model file.",
        )

    model_id = str(uuid.uuid4())
    stored_filename = f"{model_id}{ext}"
    file_path = os.path.join(STORAGE_DIR, stored_filename)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(contents)

    record = UploadedModel(
        model_id=model_id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_type=EXT_TO_FILETYPE[ext],
        file_size=file_size,
        upload_status=UploadStatus.validated,
    )

    db.add(record)
    await db.flush()
    await db.refresh(record)

    logger.info(f"Uploaded: {model_id} | {file.filename} | {file_size} bytes")
    return record


async def get_model_by_id(model_id: str, db: AsyncSession) -> UploadedModel:
    result = await db.execute(
        select(UploadedModel).where(UploadedModel.model_id == model_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model {model_id} not found.",
        )
    return record
