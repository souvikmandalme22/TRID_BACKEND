import numpy as np
import trimesh
from dataclasses import dataclass
from typing import List


# ---------- Data Structures ----------

@dataclass
class OrientationCandidate:
    index: int
    direction: np.ndarray       # unit vector pointing "up" (build direction)
    rotation_matrix: np.ndarray
    support_area: float
    print_height: float
    bed_stability: float
    overhang_risk: float
    score: float


# ---------- Fibonacci Sampling ----------

def fibonacci_sphere_directions(n_samples: int = 100) -> np.ndarray:
    """Generate n_samples evenly distributed unit vectors using Fibonacci lattice."""
    golden = (1 + np.sqrt(5)) / 2
    i = np.arange(n_samples)
    theta = np.arccos(1 - 2 * (i + 0.5) / n_samples)   # polar
    phi = 2 * np.pi * i / golden                          # azimuthal
    x = np.sin(theta) * np.cos(phi)
    y = np.sin(theta) * np.sin(phi)
    z = np.cos(theta)
    return np.stack([x, y, z], axis=1)


# ---------- Rotation Utilities ----------

def rotation_matrix_from_up_vector(up: np.ndarray) -> np.ndarray:
    """Build 3x3 rotation matrix that aligns Z-axis with the given up vector."""
    up = up / (np.linalg.norm(up) + 1e-12)
    z = np.array([0.0, 0.0, 1.0])

    cross = np.cross(z, up)
    cross_norm = np.linalg.norm(cross)

    if cross_norm < 1e-9:
        # Already aligned or anti-aligned
        return np.eye(3) if np.dot(z, up) > 0 else np.diag([1.0, -1.0, -1.0])

    axis = cross / cross_norm
    angle = np.arccos(np.clip(np.dot(z, up), -1.0, 1.0))

    # Rodrigues' rotation formula
    K = np.array([
        [0, -axis[2], axis[1]],
        [axis[2], 0, -axis[0]],
        [-axis[1], axis[0], 0],
    ])
    return np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)


def apply_rotation(mesh: trimesh.Trimesh, R: np.ndarray) -> trimesh.Trimesh:
    """Return a rotated copy of mesh without modifying original."""
    rotated = mesh.copy()
    T = np.eye(4)
    T[:3, :3] = R
    rotated.apply_transform(T)
    return rotated


# ---------- Scoring Metrics ----------

OVERHANG_THRESHOLD_DEG = 45.0


def compute_support_area(mesh: trimesh.Trimesh) -> float:
    """Area of faces that require support (normals pointing downward > threshold)."""
    normals = mesh.face_normals
    areas = mesh.area_faces
    cos_thresh = -np.cos(np.radians(OVERHANG_THRESHOLD_DEG))
    downward_mask = normals[:, 2] < cos_thresh
    return float(np.sum(areas[downward_mask]))


def compute_print_height(mesh: trimesh.Trimesh) -> float:
    """Z-extent of the mesh after rotation (lower = better)."""
    return float(mesh.extents[2])


def compute_bed_stability(mesh: trimesh.Trimesh) -> float:
    """
    Ratio of footprint area to total bounding box base area.
    Higher = more stable on bed.
    """
    bounds = mesh.bounds
    z_min = bounds[0][2]
    tolerance = mesh.extents[2] * 0.01

    vertices = mesh.vertices
    bottom_verts = vertices[vertices[:, 2] <= z_min + tolerance]

    if len(bottom_verts) < 3:
        return 0.0

    try:
        from scipy.spatial import ConvexHull
        hull = ConvexHull(bottom_verts[:, :2])
        footprint_area = float(hull.volume)  # 2D hull → volume = area
    except Exception:
        dx = float(np.ptp(bottom_verts[:, 0])) + 1e-9
        dy = float(np.ptp(bottom_verts[:, 1])) + 1e-9
        footprint_area = dx * dy

    base_area = float(mesh.extents[0] * mesh.extents[1]) + 1e-9
    return min(footprint_area / base_area, 1.0)


def compute_overhang_risk(mesh: trimesh.Trimesh) -> float:
    """Fraction of total surface area that is overhanging."""
    total_area = float(mesh.area) + 1e-9
    support_area = compute_support_area(mesh)
    return min(support_area / total_area, 1.0)


# ---------- Scoring Weights ----------

WEIGHTS = {
    "support_area":   0.35,
    "print_height":   0.25,
    "bed_stability":  0.25,
    "overhang_risk":  0.15,
}


def _normalise(value: float, all_values: List[float], lower_is_better: bool = True) -> float:
    lo, hi = min(all_values), max(all_values)
    if hi - lo < 1e-9:
        return 1.0
    normalised = (value - lo) / (hi - lo)
    return 1.0 - normalised if lower_is_better else normalised


def score_candidates(candidates: List[OrientationCandidate]) -> List[OrientationCandidate]:
    """Normalise metrics across all candidates and compute composite score."""
    support_areas  = [c.support_area   for c in candidates]
    print_heights  = [c.print_height   for c in candidates]
    bed_stabilities = [c.bed_stability for c in candidates]
    overhang_risks = [c.overhang_risk  for c in candidates]

    for c in candidates:
        s = (
            WEIGHTS["support_area"]  * _normalise(c.support_area,  support_areas,  lower_is_better=True)
          + WEIGHTS["print_height"]  * _normalise(c.print_height,  print_heights,  lower_is_better=True)
          + WEIGHTS["bed_stability"] * _normalise(c.bed_stability, bed_stabilities, lower_is_better=False)
          + WEIGHTS["overhang_risk"] * _normalise(c.overhang_risk, overhang_risks, lower_is_better=True)
        )
        c.score = round(s, 6)

    return candidates


# ---------- Main Engine ----------

def run_orientation_sampling(
    mesh: trimesh.Trimesh,
    n_samples: int = 100,
) -> List[OrientationCandidate]:
    """
    Generate n_samples orientations via Fibonacci sampling,
    evaluate each, return scored list sorted best-first.
    """
    directions = fibonacci_sphere_directions(n_samples)
    candidates: List[OrientationCandidate] = []

    for idx, direction in enumerate(directions):
        R = rotation_matrix_from_up_vector(direction)
        rotated = apply_rotation(mesh, R)

        candidate = OrientationCandidate(
            index=idx,
            direction=direction,
            rotation_matrix=R,
            support_area=compute_support_area(rotated),
            print_height=compute_print_height(rotated),
            bed_stability=compute_bed_stability(rotated),
            overhang_risk=compute_overhang_risk(rotated),
            score=0.0,
        )
        candidates.append(candidate)

    return score_candidates(candidates)


def get_best_orientation(candidates: List[OrientationCandidate]) -> OrientationCandidate:
    return max(candidates, key=lambda c: c.score)
