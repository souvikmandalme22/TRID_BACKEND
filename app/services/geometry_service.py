import asyncio
import logging
from functools import partial

import trimesh
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.geometry import GeometryAnalysis
from app.models.upload import UploadedModel, UploadStatus
from app.schemas.geometry import GeometryAnalysisResponse

logger = logging.getLogger("trid")


def _load_and_analyse(file_path: str) -> dict:
    try:
        mesh = trimesh.load(file_path, force="mesh")
    except Exception as e:
        raise ValueError(f"Failed to load mesh: {e}")

    if mesh is None or (hasattr(mesh, "is_empty") and mesh.is_empty):
        raise ValueError("Empty or unreadable geometry.")

    if isinstance(mesh, trimesh.Scene):
        geometries = list(mesh.geometry.values())
        if not geometries:
            raise ValueError("No geometry found in scene.")
        mesh = trimesh.util.concatenate(geometries)

    bounds = mesh.bounds
    extents = mesh.extents
    volume = float(mesh.volume) if mesh.is_watertight else float(mesh.convex_hull.volume)

    return {
        "dim_x": round(float(extents[0]), 4),
        "dim_y": round(float(extents[1]), 4),
        "dim_z": round(float(extents[2]), 4),
        "bbox_min_x": round(float(bounds[0][0]), 4),
        "bbox_min_y": round(float(bounds[0][1]), 4),
        "bbox_min_z": round(float(bounds[0][2]), 4),
        "bbox_max_x": round(float(bounds[1][0]), 4),
        "bbox_max_y": round(float(bounds[1][1]), 4),
        "bbox_max_z": round(float(bounds[1][2]), 4),
        "volume": round(volume, 4),
        "surface_area": round(float(mesh.area), 4),
        "is_watertight": bool(mesh.is_watertight),
    }


async def run_geometry_analysis(model_id: str, db: AsyncSession) -> GeometryAnalysisResponse:
    result = await db.execute(select(UploadedModel).where(UploadedModel.model_id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found.")

    existing = await db.execute(select(GeometryAnalysis).where(GeometryAnalysis.model_id == model_id))
    analysis = existing.scalar_one_or_none()

    if analysis and analysis.analysis_status == "completed":
        return GeometryAnalysisResponse.from_orm_model(analysis)

    if not analysis:
        analysis = GeometryAnalysis(model_id=model_id, analysis_status="processing")
        db.add(analysis)
        await db.flush()
    else:
        analysis.analysis_status = "processing"

    try:
        loop = asyncio.get_event_loop()
        metrics = await loop.run_in_executor(None, partial(_load_and_analyse, model.file_path))

        for key, val in metrics.items():
            setattr(analysis, key, val)

        analysis.analysis_status = "completed"
        analysis.error_message = None
        model.upload_status = UploadStatus.ready

        await db.flush()
        await db.refresh(analysis)
        logger.info(f"Geometry analysis complete: {model_id}")
        return GeometryAnalysisResponse.from_orm_model(analysis)

    except Exception as e:
        analysis.analysis_status = "failed"
        analysis.error_message = str(e)[:512]
        await db.flush()
        logger.error(f"Geometry analysis failed [{model_id}]: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Geometry analysis failed: {e}",
        )


async def get_analysis_by_model_id(model_id: str, db: AsyncSession) -> GeometryAnalysisResponse:
    result = await db.execute(select(GeometryAnalysis).where(GeometryAnalysis.model_id == model_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    return GeometryAnalysisResponse.from_orm_model(analysis)
