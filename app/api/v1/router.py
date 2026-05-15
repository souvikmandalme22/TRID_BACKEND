from fastapi import APIRouter
from app.api.v1.endpoints import (
    health, upload, geometry, orientation,
    support, support_density, segment,
    material_family, material, use_case,
    recommendation, infill, effective_material,
    pricing, payments,
)

router = APIRouter()
router.include_router(health.router,             tags=["Health"])
router.include_router(upload.router,             tags=["Upload"])
router.include_router(geometry.router,           tags=["Geometry Analysis"])
router.include_router(orientation.router,        tags=["Orientation Engine"])
router.include_router(support.router,            tags=["Support Estimation"])
router.include_router(support_density.router,    tags=["Support Density"])
router.include_router(segment.router,            tags=["Segments"])
router.include_router(material_family.router,    tags=["Material Families"])
router.include_router(material.router,           tags=["Materials"])
router.include_router(use_case.router,           tags=["Use Cases"])
router.include_router(recommendation.router,     tags=["Recommendations"])
router.include_router(infill.router,             tags=["Infill"])
router.include_router(effective_material.router, tags=["Effective Material"])
router.include_router(pricing.router,            tags=["Pricing"])
router.include_router(payments.router,           tags=["Payments"])
