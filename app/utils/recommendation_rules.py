"""
Rule-based recommendation engine.
Each rule is a pure function: (segment_slug, use_case_slug, environment_tags, family_slug) → score modifier + warnings.
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class RuleResult:
    score_boost: float = 0.0
    score_penalty: float = 0.0
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# ---------- Segment rules ----------

SEGMENT_PREFERRED_MATERIALS: dict[str, list[str]] = {
    "jewelry":       ["castable-wax-resin", "high-detail-resin", "clear-resin"],
    "medical":       ["nylon", "tough-resin", "high-detail-resin"],
    "engineering":   ["nylon", "petg", "abs"],
    "automotive":    ["abs", "nylon", "petg"],
    "robotics":      ["nylon", "petg", "tpu"],
    "industrial":    ["nylon", "abs", "petg"],
    "architecture":  ["pla", "petg", "standard-resin"],
    "consumer":      ["pla", "petg", "tpu"],
}

SEGMENT_AVOID_MATERIALS: dict[str, list[str]] = {
    "jewelry":   ["pla", "abs", "petg"],
    "medical":   ["pla", "flexible-resin"],
    "industrial":["pla", "standard-resin", "clear-resin"],
}

# ---------- Use-case strength rules ----------

USE_CASE_MIN_STRENGTH: dict[str, str] = {
    "showpiece":    "low",
    "fit-assembly": "medium",
    "daily-use":    "high",
    "heavy-duty":   "ultra",
}

STRENGTH_RANK = {"low": 0, "medium": 1, "high": 2, "ultra": 3}

# ---------- Environment rules ----------

OUTDOOR_UNSAFE_MATERIALS = {"pla", "standard-resin", "clear-resin", "flexible-resin", "high-detail-resin", "castable-wax-resin"}
HEAT_UNSAFE_MATERIALS    = {"pla", "standard-resin", "clear-resin", "flexible-resin", "castable-wax-resin", "tpu"}
NEAR_HEAT_SAFE_MATERIALS = {"abs", "nylon", "tough-resin", "petg"}

# ---------- Family-use-case compatibility ----------

RESIN_FAMILY_SLUG = "resin"
RESIN_INCOMPATIBLE_USE_CASES = {"heavy-duty", "daily-use"}   # general resins → warn


def evaluate_material(
    material_slug: str,
    material_strength: str,
    material_outdoor: bool,
    material_heat: bool,
    family_slug: str,
    segment_slug: str,
    use_case_slug: str,
    environment_tags: List[str],
) -> RuleResult:
    result = RuleResult()

    # --- Segment preference ---
    preferred = SEGMENT_PREFERRED_MATERIALS.get(segment_slug, [])
    avoided   = SEGMENT_AVOID_MATERIALS.get(segment_slug, [])

    if material_slug in preferred:
        result.score_boost += 0.40
    if material_slug in avoided:
        result.score_penalty += 0.35
        result.warnings.append(f"'{material_slug}' is not ideal for {segment_slug} applications.")

    # --- Use-case strength gate ---
    required_strength = USE_CASE_MIN_STRENGTH.get(use_case_slug, "low")
    if STRENGTH_RANK.get(material_strength, 0) < STRENGTH_RANK.get(required_strength, 0):
        result.score_penalty += 0.40
        result.warnings.append(
            f"This material's strength ({material_strength}) may not meet the demands of '{use_case_slug}'. "
            f"Consider a '{required_strength}' strength material."
        )

    # --- Environment: outdoor ---
    if "outdoor" in environment_tags:
        if material_slug in OUTDOOR_UNSAFE_MATERIALS:
            result.score_penalty += 0.30
            result.warnings.append(f"'{material_slug}' degrades under UV/moisture. Not recommended for outdoor use.")
        elif material_outdoor:
            result.score_boost += 0.20

    # --- Environment: near heat ---
    if "near-heat" in environment_tags or "near_heat" in environment_tags:
        if material_slug in HEAT_UNSAFE_MATERIALS:
            result.score_penalty += 0.25
            result.warnings.append(f"'{material_slug}' has low heat resistance. Avoid near heat sources.")
        elif material_heat:
            result.score_boost += 0.20

    # --- Resin + heavy use-case warning ---
    if family_slug == RESIN_FAMILY_SLUG and use_case_slug in RESIN_INCOMPATIBLE_USE_CASES:
        if material_slug not in {"tough-resin"}:
            result.score_penalty += 0.20
            result.warnings.append(
                f"Most resins are brittle for '{use_case_slug}'. Consider engineering plastics like Nylon or PETG."
            )

    # --- Segment-specific suggestions ---
    if segment_slug == "jewelry" and material_slug not in preferred:
        result.suggestions.append("For jewelry, Castable Wax Resin or High Detail Resin gives best results.")
    if segment_slug == "medical" and material_slug == "pla":
        result.suggestions.append("PLA is not biocompatible. For medical use, consider Nylon or medical-grade resin.")
    if use_case_slug == "heavy-duty" and material_slug == "pla":
        result.suggestions.append("For heavy-duty applications, consider Nylon or ABS for better durability.")

    return result
