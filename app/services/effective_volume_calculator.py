"""
TRID — Effective Volume Calculator
app/services/effective_volume_calculator.py

Converts raw STL geometry (mesh_volume, surface_area, bounding_box)
into accurate final_effective_material_cc for the pricing engine.

Core insight:
  - Raw mesh_volume = solid body volume (WRONG for pricing)
  - Effective volume = only what actually gets printed (shell + infill)
  - Large/hollow parts massively overcharged if mesh_volume is used directly

Requirements already in requirements.txt:
  trimesh==4.3.2
  numpy==1.26.4
  scipy==1.11.4
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

WALL_THICKNESS_CM      = 0.12    # 3 perimeters × 0.4mm nozzle = 1.2mm
SUPPORT_INFILL_DENSITY = 0.15    # support structures print at ~15% density
STRUCTURAL_RIB_FACTOR  = 0.08    # extra 8% inner volume for cross-bracing in structural parts

# S/V thresholds (cm²/cm³) for part type detection
SV_THIN_WALL_THRESHOLD   = 0.50  # above this → hollow/thin-wall
SV_STRUCTURAL_THRESHOLD  = 0.25  # above this (but below thin_wall) → structural

# Size thresholds
LARGE_PART_DIM_CM   = 15.0       # longest side > 15cm → treat as large
LARGE_PART_VOL_CM3  = 1000.0     # bounding box volume > 1000 cm³ → large

MATERIAL_DENSITY: dict[str, float] = {
    "PLA":        1.24,
    "ABS":        1.04,
    "PETG":       1.27,
    "TPU":        1.20,
    "NYLON_PA12": 1.01,
    "RESIN":      1.10,
}

# Approximate cm³ of effective material deposited per hour
PRINT_SPEED_CC_PER_HR: dict[str, float] = {
    "draft":    12.0,
    "standard":  8.0,
    "fine":      3.5,
}

MACHINE_HOURLY_RATE_INR: dict[str, float] = {
    "desktop":      90.0,
    "mid_industry": 140.0,
    "industry":     250.0,
}


# ─────────────────────────────────────────────
# PART TYPE
# ─────────────────────────────────────────────

class PartType(str, Enum):
    SOLID      = "solid"       # Gear, bracket → infill dominant
    THIN_WALL  = "thin_wall"   # Box, enclosure, cover → shell walls only
    STRUCTURAL = "structural"  # Architectural, furniture → shell + moderate infill


# ─────────────────────────────────────────────
# INPUT
# ─────────────────────────────────────────────

@dataclass
class STLGeometry:
    """
    Populated from trimesh after file upload.

    Example (in your upload route):
        import trimesh
        mesh = trimesh.load(file_path)
        extents_cm = mesh.bounding_box.extents / 10  # mm → cm

        geom = STLGeometry(
            mesh_volume_cc    = mesh.volume / 1000,      # mm³ → cm³
            surface_area_cm2  = mesh.area / 100,         # mm² → cm²
            bbox_x_cm         = extents_cm[0],
            bbox_y_cm         = extents_cm[1],
            bbox_z_cm         = extents_cm[2],
            support_volume_cc = <from your support engine output>,
            infill_percent    = <user selection 10-100>,
            quality           = <"draft"|"standard"|"fine">,
            machine_tier      = <"desktop"|"mid_industry"|"industry">,
            material_key      = <"PLA"|"ABS"|"PETG"|"TPU"|"NYLON_PA12"|"RESIN">,
        )
    """
    mesh_volume_cc:    float
    surface_area_cm2:  float
    bbox_x_cm:         float
    bbox_y_cm:         float
    bbox_z_cm:         float
    support_volume_cc: float
    infill_percent:    float    # 10 – 100
    quality:           str      # "draft" | "standard" | "fine"
    machine_tier:      str      # "desktop" | "mid_industry" | "industry"
    material_key:      str      # "PLA" | "ABS" | etc.


# ─────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────

@dataclass
class VolumeResult:
    # → goes directly into PricingRequest.final_effective_material_cc
    final_effective_material_cc: float

    part_type:             PartType
    sv_ratio:              float
    shell_volume_cc:       float
    infill_volume_cc:      float
    support_effective_cc:  float
    print_time_hrs:        float
    machine_time_cost_inr: float
    material_weight_grams: float

    # Useful for frontend breakdown / debugging
    raw_mesh_volume_cc:    float
    savings_vs_raw:        float    # how many CC saved vs naive calculation
    debug: dict = field(default_factory=dict)


# ─────────────────────────────────────────────
# CALCULATOR
# ─────────────────────────────────────────────

class EffectiveVolumeCalculator:
    """
    Main class. Call .calculate(geom) to get VolumeResult.
    """

    def calculate(self, geom: STLGeometry) -> VolumeResult:
        self._validate(geom)

        # 1. Detect part type
        part_type, sv_ratio = self._detect_part_type(geom)
        logger.info(f"[VolumeCalc] part_type={part_type.value} sv_ratio={sv_ratio:.3f}")

        # 2. Shell + infill volume
        shell_vol, infill_vol = self._calc_printed_volume(geom, part_type)

        # 3. Support (already computed by your support engine)
        support_eff = round(geom.support_volume_cc * SUPPORT_INFILL_DENSITY, 3)

        # 4. Total effective CC
        total_cc = shell_vol + infill_vol + support_eff

        # 5. Print time & machine cost
        speed    = PRINT_SPEED_CC_PER_HR.get(geom.quality, 8.0)
        pt_hrs   = total_cc / speed if speed > 0 else 0.0
        hourly   = MACHINE_HOURLY_RATE_INR.get(geom.machine_tier, 90.0)
        mc_cost  = pt_hrs * hourly

        # 6. Weight
        density = MATERIAL_DENSITY.get(geom.material_key.upper(), 1.0)
        weight  = total_cc * density

        savings = max(0.0, geom.mesh_volume_cc - total_cc)

        return VolumeResult(
            final_effective_material_cc = round(total_cc, 2),
            part_type                   = part_type,
            sv_ratio                    = round(sv_ratio, 4),
            shell_volume_cc             = round(shell_vol, 2),
            infill_volume_cc            = round(infill_vol, 2),
            support_effective_cc        = round(support_eff, 2),
            print_time_hrs              = round(pt_hrs, 2),
            machine_time_cost_inr       = round(mc_cost, 2),
            material_weight_grams       = round(weight, 2),
            raw_mesh_volume_cc          = geom.mesh_volume_cc,
            savings_vs_raw              = round(savings, 2),
            debug={
                "bbox_cm":         f"{geom.bbox_x_cm:.1f}×{geom.bbox_y_cm:.1f}×{geom.bbox_z_cm:.1f}",
                "infill_percent":  geom.infill_percent,
                "quality":         geom.quality,
                "machine_tier":    geom.machine_tier,
                "raw_support_cc":  geom.support_volume_cc,
            },
        )

    # ── PART TYPE DETECTION ───────────────────────────────────────────────

    def _detect_part_type(self, geom: STLGeometry) -> tuple[PartType, float]:
        """
        Uses Surface-to-Volume ratio + bounding box size.

        S/V ratio intuition:
          Solid sphere (most compact):  ~0.07
          Solid cube:                   ~0.24
          Thin-walled box/enclosure:    0.50 – 2.0+
          Very thin architectural wall: 5.0+

        Size override: even a "dense" S/V part is treated as large
        if bounding box is huge — because real-world large prints are
        always hollowed out by the printer.
        """
        sv = (geom.surface_area_cm2 / geom.mesh_volume_cc
              if geom.mesh_volume_cc > 0 else 999.0)

        longest = max(geom.bbox_x_cm, geom.bbox_y_cm, geom.bbox_z_cm)
        bbox_vol = geom.bbox_x_cm * geom.bbox_y_cm * geom.bbox_z_cm
        is_large = (longest > LARGE_PART_DIM_CM) or (bbox_vol > LARGE_PART_VOL_CM3)

        if is_large or sv > SV_THIN_WALL_THRESHOLD:
            # Further split: very thin vs structural hollow
            if sv > 0.80 or longest > 25.0:
                return PartType.THIN_WALL, sv
            else:
                return PartType.STRUCTURAL, sv
        else:
            return PartType.SOLID, sv

    # ── PRINTED VOLUME ────────────────────────────────────────────────────

    def _calc_printed_volume(
        self, geom: STLGeometry, part_type: PartType
    ) -> tuple[float, float]:
        """
        Returns (shell_volume_cc, infill_volume_cc).

        SOLID:      normal infill fills the interior
        THIN_WALL:  interior is air; only perimeter walls printed
                    (capped at 10% infill even if user selects more)
        STRUCTURAL: partial infill for strength, but still mostly hollow
        """
        sa      = geom.surface_area_cm2
        mv      = geom.mesh_volume_cc
        infill  = geom.infill_percent / 100.0

        # Shell = surface area × wall thickness
        shell = sa * WALL_THICKNESS_CM
        shell = min(shell, mv * 0.95)   # safety: can't exceed total volume

        inner = max(0.0, mv - shell)

        if part_type == PartType.SOLID:
            infill_vol = inner * infill

        elif part_type == PartType.THIN_WALL:
            # Box / enclosure / cover — hollow by design
            # Cap infill effect to 10% regardless of user setting
            effective_infill = min(infill, 0.10)
            infill_vol = inner * effective_infill

        elif part_type == PartType.STRUCTURAL:
            # Architectural / furniture — needs some internal bracing
            # Rib factor (8%) + 30% of user infill (not full, part is still hollow)
            infill_vol = inner * (STRUCTURAL_RIB_FACTOR + infill * 0.30)

        else:
            infill_vol = inner * infill

        return round(shell, 3), round(infill_vol, 3)

    # ── VALIDATION ────────────────────────────────────────────────────────

    def _validate(self, geom: STLGeometry) -> None:
        if geom.mesh_volume_cc <= 0:
            raise ValueError("mesh_volume_cc must be > 0")
        if geom.surface_area_cm2 <= 0:
            raise ValueError("surface_area_cm2 must be > 0")
        if not (0 <= geom.infill_percent <= 100):
            raise ValueError("infill_percent must be 0-100")
        if geom.quality not in PRINT_SPEED_CC_PER_HR:
            raise ValueError(f"quality must be one of {list(PRINT_SPEED_CC_PER_HR)}")
        if geom.machine_tier not in MACHINE_HOURLY_RATE_INR:
            raise ValueError(f"machine_tier must be one of {list(MACHINE_HOURLY_RATE_INR)}")
