import asyncio
import logging
from functools import partial

import trimesh
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.support import SupportAnalysis
from app.models.upload import UploadedModel
from app.models.orientation import OrientationResult
from app.schemas.support import SupportAnalysisResponse
from app.utils.support_engine import estimate_supports

logger = logging.getLogger("trid")


def _run_sync(file_path: str, direction: tuple) -> dict:
    mesh = trimesh.load(file_path, force="mesh")
    if mesh is None or (hasattr(mesh, "is_empty") and mesh.is_empty):
        raise ValueError("Empty or invalid mesh.")

    if isinstance(mesh, trimesh.Scene):
        geometries = list(mesh.geometry.values())
        if not geometries:
            raise ValueError("No geometry in scene.")
        mesh = trimesh.util.concatenate(geometries)

    result = estimate_supports(mesh, direction)
    return {
        "raw_support_volume":  result.raw_support_volume,
        "support_area":        result.support_area,
        "print_height":        result.print_height,
        "overhang_face_count": result.overhang_face_count,
    }


async def run_support_analysis(model_id: str, db: AsyncSession) -> SupportAnalysisResponse:
    # Fetch model
    res = await db.execute(select(UploadedModel).where(UploadedModel.model_id == model_id))
    model = res.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found.")

    # Require orientation to be done first
    ori = await db.execute(select(OrientationResult).where(OrientationResult.model_id == model_id))
    orientation = ori.scalar_one_or_none()
    if not orientation or orientation.analysis_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Orientation analysis must be completed before support estimation.",
        )

    # Check existing
    existing = await db.execute(select(SupportAnalysis).where(SupportAnalysis.model_id == model_id))
    record = existing.scalar_one_or_none()

    if record and record.analysis_status == "completed":
        return SupportAnalysisResponse.from_orm_model(record)

    if not record:
        record = SupportAnalysis(model_id=model_id, analysis_status="processing")
        db.add(record)
        await db.flush()
    else:
        record.analysis_status = "processing"

    direction = (orientation.best_direction_x, orientation.best_direction_y, orientation.best_direction_z)

    try:
        loop = asyncio.get_event_loop()
        metrics = await loop.run_in_executor(None, partial(_run_sync, model.file_path, direction))

        for key, val in metrics.items():
            setattr(record, key, val)

        record.analysis_status = "completed"
        record.error_message = None
        await db.flush()
        await db.refresh(record)

        logger.info(f"Support analysis complete: {model_id} | vol={metrics['raw_support_volume']} mm³")
        return SupportAnalysisResponse.from_orm_model(record)

    except Exception as e:
        record.analysis_status = "failed"
        record.error_message = str(e)[:512]
        await db.flush()
        logger.error(f"Support analysis failed [{model_id}]: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Support analysis failed: {e}",
        )


async def get_support_by_model_id(model_id: str, db: AsyncSession) -> SupportAnalysisResponse:
    result = await db.execute(select(SupportAnalysis).where(SupportAnalysis.model_id == model_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support analysis not found.")
    return SupportAnalysisResponse.from_orm_model(record)
