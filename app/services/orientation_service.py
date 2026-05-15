import asyncio
import logging
from functools import partial

import trimesh
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.orientation import OrientationResult
from app.models.upload import UploadedModel
from app.schemas.orientation import OrientationResultResponse
from app.utils.orientation_engine import run_orientation_sampling, get_best_orientation

logger = logging.getLogger("trid")

N_SAMPLES = 100


def _run_sync(file_path: str) -> dict:
    mesh = trimesh.load(file_path, force="mesh")
    if mesh is None or (hasattr(mesh, "is_empty") and mesh.is_empty):
        raise ValueError("Empty or invalid mesh for orientation analysis.")

    if isinstance(mesh, trimesh.Scene):
        geometries = list(mesh.geometry.values())
        if not geometries:
            raise ValueError("No geometry found in scene.")
        mesh = trimesh.util.concatenate(geometries)

    candidates = run_orientation_sampling(mesh, n_samples=N_SAMPLES)
    best = get_best_orientation(candidates)

    return {
        "best_direction_x": round(float(best.direction[0]), 6),
        "best_direction_y": round(float(best.direction[1]), 6),
        "best_direction_z": round(float(best.direction[2]), 6),
        "support_area":      round(best.support_area, 4),
        "print_height":      round(best.print_height, 4),
        "bed_stability":     round(best.bed_stability, 6),
        "overhang_risk":     round(best.overhang_risk, 6),
        "orientation_score": round(best.score, 6),
        "n_samples_evaluated": N_SAMPLES,
    }


async def run_orientation_analysis(model_id: str, db: AsyncSession) -> OrientationResultResponse:
    result = await db.execute(select(UploadedModel).where(UploadedModel.model_id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found.")

    existing = await db.execute(select(OrientationResult).where(OrientationResult.model_id == model_id))
    record = existing.scalar_one_or_none()

    if record and record.analysis_status == "completed":
        return OrientationResultResponse.from_orm_model(record)

    if not record:
        record = OrientationResult(model_id=model_id, analysis_status="processing")
        db.add(record)
        await db.flush()
    else:
        record.analysis_status = "processing"

    try:
        loop = asyncio.get_event_loop()
        metrics = await loop.run_in_executor(None, partial(_run_sync, model.file_path))

        for key, val in metrics.items():
            setattr(record, key, val)

        record.analysis_status = "completed"
        record.error_message = None
        await db.flush()
        await db.refresh(record)

        logger.info(f"Orientation analysis complete: {model_id} | score={metrics['orientation_score']}")
        return OrientationResultResponse.from_orm_model(record)

    except Exception as e:
        record.analysis_status = "failed"
        record.error_message = str(e)[:512]
        await db.flush()
        logger.error(f"Orientation analysis failed [{model_id}]: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Orientation analysis failed: {e}",
        )


async def get_orientation_by_model_id(model_id: str, db: AsyncSession) -> OrientationResultResponse:
    result = await db.execute(select(OrientationResult).where(OrientationResult.model_id == model_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orientation result not found.")
    return OrientationResultResponse.from_orm_model(record)
