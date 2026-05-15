import numpy as np
import trimesh
from dataclasses import dataclass


OVERHANG_ANGLE_DEG = 45.0          # faces beyond this need support
SUPPORT_COLUMN_DENSITY = 1.0       # support columns treated as solid beneath overhang


@dataclass
class SupportEstimate:
    raw_support_volume: float      # mm³  — geometric column volume beneath overhangs
    support_area: float            # mm²  — total overhang face area needing support
    print_height: float            # mm   — Z-extent in best orientation
    overhang_face_count: int


def _apply_best_orientation(mesh: trimesh.Trimesh, direction: tuple) -> trimesh.Trimesh:
    """Rotate mesh so that best build direction aligns with +Z."""
    from app.utils.orientation_engine import rotation_matrix_from_up_vector
    up = np.array(direction, dtype=float)
    R = rotation_matrix_from_up_vector(up)
    rotated = mesh.copy()
    T = np.eye(4)
    T[:3, :3] = R
    rotated.apply_transform(T)
    return rotated


def _detect_overhang_faces(mesh: trimesh.Trimesh) -> tuple[np.ndarray, np.ndarray]:
    """
    Return mask and face areas for faces that require support.
    A face needs support when its downward normal component exceeds the overhang threshold.
    """
    normals = mesh.face_normals          # (N, 3)
    areas   = mesh.area_faces            # (N,)
    cos_thresh = -np.cos(np.radians(OVERHANG_ANGLE_DEG))
    # faces pointing downward more than threshold
    mask = normals[:, 2] < cos_thresh
    return mask, areas


def _estimate_support_volume(mesh: trimesh.Trimesh, overhang_mask: np.ndarray) -> float:
    """
    Estimate raw support volume by projecting each overhang face down to the print bed.
    Volume = sum over overhang faces of (face_area × height_above_bed).
    This gives the geometric bounding column volume beneath each overhang region.
    """
    if not np.any(overhang_mask):
        return 0.0

    face_indices = np.where(overhang_mask)[0]
    triangles    = mesh.triangles[face_indices]          # (K, 3, 3)
    face_areas   = mesh.area_faces[face_indices]         # (K,)

    z_min_global = float(mesh.bounds[0][2])

    # centroid Z of each overhang triangle
    centroid_z = triangles[:, :, 2].mean(axis=1)         # (K,)
    heights    = np.maximum(centroid_z - z_min_global, 0.0)

    volume = float(np.sum(face_areas * heights))
    return round(volume, 4)


def estimate_supports(
    mesh: trimesh.Trimesh,
    best_direction: tuple,           # (dx, dy, dz) from orientation engine
) -> SupportEstimate:
    """
    Full support estimation pipeline:
    1. Rotate mesh to best orientation
    2. Detect overhang faces
    3. Estimate support column volume
    """
    rotated = _apply_best_orientation(mesh, best_direction)

    overhang_mask, face_areas = _detect_overhang_faces(rotated)

    support_area        = float(np.sum(face_areas[overhang_mask]))
    raw_support_volume  = _estimate_support_volume(rotated, overhang_mask)
    print_height        = float(rotated.extents[2])
    overhang_face_count = int(np.sum(overhang_mask))

    return SupportEstimate(
        raw_support_volume=round(raw_support_volume, 4),
        support_area=round(support_area, 4),
        print_height=round(print_height, 4),
        overhang_face_count=overhang_face_count,
    )
