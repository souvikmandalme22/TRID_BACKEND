from dataclasses import dataclass
from enum import Enum


class InfillProfile(str, Enum):
    lightweight = "10"    # 10%
    standard    = "20"    # 20%
    strong      = "40"    # 40%
    industrial  = "60"    # 60%
    solid       = "100"   # 100%


INFILL_FACTORS: dict[InfillProfile, float] = {
    InfillProfile.lightweight: 0.10,
    InfillProfile.standard:    0.20,
    InfillProfile.strong:      0.40,
    InfillProfile.industrial:  0.60,
    InfillProfile.solid:       1.00,
}

INFILL_LABELS: dict[InfillProfile, str] = {
    InfillProfile.lightweight: "10% — Lightweight",
    InfillProfile.standard:    "20% — Standard",
    InfillProfile.strong:      "40% — Strong",
    InfillProfile.industrial:  "60% — Industrial",
    InfillProfile.solid:       "100% — Solid",
}

# Shell walls always printed solid — outer shell adds ~15% fixed overhead
SHELL_OVERHEAD_FACTOR = 0.15


@dataclass
class InfillResult:
    model_volume:              float    # mm³ raw geometry volume
    infill_profile:            InfillProfile
    infill_percentage:         int
    infill_factor:             float
    effective_model_material:  float    # mm³ actual filament used
    is_resin:                  bool


def calculate_infill(
    model_volume: float,
    infill_profile: InfillProfile,
    is_resin: bool = False,
) -> InfillResult:
    if model_volume <= 0:
        raise ValueError("model_volume must be positive.")

    if is_resin:
        # Resin is printed solid — infill does not apply
        return InfillResult(
            model_volume=model_volume,
            infill_profile=InfillProfile.solid,
            infill_percentage=100,
            infill_factor=1.0,
            effective_model_material=round(model_volume, 4),
            is_resin=True,
        )

    factor = INFILL_FACTORS[infill_profile]
    # effective = shell overhead (always solid) + infill portion of inner volume
    effective = model_volume * (SHELL_OVERHEAD_FACTOR + (1 - SHELL_OVERHEAD_FACTOR) * factor)

    return InfillResult(
        model_volume=model_volume,
        infill_profile=infill_profile,
        infill_percentage=int(infill_profile.value),
        infill_factor=factor,
        effective_model_material=round(effective, 4),
        is_resin=False,
    )
