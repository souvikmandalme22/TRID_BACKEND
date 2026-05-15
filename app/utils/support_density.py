from enum import Enum
from dataclasses import dataclass


class MaterialCategory(str, Enum):
    filament = "filament"
    resin = "resin"


class SupportDensityProfile(str, Enum):
    light  = "light"
    normal = "normal"
    dense  = "dense"


# Density factors per profile per material category
DENSITY_FACTORS: dict[MaterialCategory, dict[SupportDensityProfile, float]] = {
    MaterialCategory.filament: {
        SupportDensityProfile.light:  0.15,   # 15% fill — fast, weak
        SupportDensityProfile.normal: 0.30,   # 30% fill — standard
        SupportDensityProfile.dense:  0.60,   # 60% fill — strong overhangs
    },
    MaterialCategory.resin: {
        # Resin supports are thin pillars — always near-solid
        SupportDensityProfile.light:  0.40,
        SupportDensityProfile.normal: 0.60,
        SupportDensityProfile.dense:  0.90,
    },
}


@dataclass
class SupportDensityResult:
    raw_support_volume: float
    density_profile: SupportDensityProfile
    material_category: MaterialCategory
    density_factor: float
    effective_support_material: float   # mm³ actual filament/resin used in supports


def calculate_support_density(
    raw_support_volume: float,
    material_category: MaterialCategory,
    density_profile: SupportDensityProfile = SupportDensityProfile.normal,
) -> SupportDensityResult:
    if raw_support_volume < 0:
        raise ValueError("raw_support_volume cannot be negative.")

    factor = DENSITY_FACTORS[material_category][density_profile]
    effective = round(raw_support_volume * factor, 4)

    return SupportDensityResult(
        raw_support_volume=raw_support_volume,
        density_profile=density_profile,
        material_category=material_category,
        density_factor=factor,
        effective_support_material=effective,
    )
