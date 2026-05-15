import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.material import Material
from app.models.material_family import MaterialFamily
from app.models.segment import Segment
from app.models.use_case import UseCase
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    MaterialRecommendation,
)
from app.utils.recommendation_rules import evaluate_material, STRENGTH_RANK

logger = logging.getLogger("trid")

BASE_SCORE = 0.50


async def _validate_inputs(segment_slug: str, use_case_slug: str, db: AsyncSession):
    seg = await db.execute(select(Segment).where(Segment.slug == segment_slug, Segment.is_active == True))
    if not seg.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Segment '{segment_slug}' not found.")
    uc = await db.execute(select(UseCase).where(UseCase.slug == use_case_slug, UseCase.is_active == True))
    if not uc.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Use case '{use_case_slug}' not found.")


async def get_recommendations(
    request: RecommendationRequest,
    db: AsyncSession,
) -> RecommendationResponse:

    await _validate_inputs(request.segment_slug, request.use_case_slug, db)

    # Load active materials + their family slugs
    mat_query = select(Material, MaterialFamily).join(
        MaterialFamily, Material.family_id == MaterialFamily.id
    ).where(Material.is_active == True)

    if request.family_slug:
        fam = await db.execute(select(MaterialFamily).where(MaterialFamily.slug == request.family_slug))
        fam_record = fam.scalar_one_or_none()
        if not fam_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Family '{request.family_slug}' not found.")
        mat_query = mat_query.where(MaterialFamily.slug == request.family_slug)

    rows = (await db.execute(mat_query)).all()

    scored: List[MaterialRecommendation] = []

    for mat, fam in rows:
        rule = evaluate_material(
            material_slug=mat.slug,
            material_strength=mat.strength_category,
            material_outdoor=mat.outdoor_suitable,
            material_heat=mat.heat_resistance,
            family_slug=fam.slug,
            segment_slug=request.segment_slug,
            use_case_slug=request.use_case_slug,
            environment_tags=request.environment_tags,
        )

        final_score = round(
            max(0.0, min(1.0, BASE_SCORE + rule.score_boost - rule.score_penalty)), 4
        )

        scored.append(MaterialRecommendation(
            material_id=mat.id,
            name=mat.name,
            slug=mat.slug,
            family_slug=fam.slug,
            short_description=mat.short_description,
            price_per_cc=mat.price_per_cc,
            strength_category=mat.strength_category,
            flexibility_category=mat.flexibility_category,
            tags=mat.tags,
            recommendation_score=final_score,
            warnings=rule.warnings,
            suggestions=rule.suggestions,
        ))

    # Sort: score desc, then price asc for ties
    scored.sort(key=lambda m: (-m.recommendation_score, m.price_per_cc))

    # Global warnings
    global_warnings: List[str] = []
    global_suggestions: List[str] = []

    if "outdoor" in request.environment_tags:
        global_warnings.append("Outdoor environment detected — UV and moisture resistance is critical.")
    if "near-heat" in request.environment_tags or "near_heat" in request.environment_tags:
        global_warnings.append("Heat exposure detected — ensure selected material has sufficient heat resistance.")
    if request.use_case_slug == "heavy-duty":
        global_suggestions.append("Heavy-duty use requires high strength. Nylon or engineering plastics are recommended.")
    if request.segment_slug == "medical":
        global_warnings.append("Medical applications may require certified biocompatible materials.")
    if request.segment_slug == "jewelry":
        global_suggestions.append("For casting, use Castable Wax Resin. For display, High Detail Resin gives best finish.")

    # Only return materials with score > 0.30 (filter out terrible matches)
    filtered = [m for m in scored if m.recommendation_score >= 0.30]
    if not filtered:
        filtered = scored[:3]  # fallback — always return at least 3

    logger.info(
        f"Recommendations: segment={request.segment_slug} use_case={request.use_case_slug} "
        f"→ {len(filtered)} materials returned"
    )

    return RecommendationResponse(
        segment_slug=request.segment_slug,
        use_case_slug=request.use_case_slug,
        environment_tags=request.environment_tags,
        recommended=filtered,
        global_warnings=global_warnings,
        global_suggestions=global_suggestions,
    )
