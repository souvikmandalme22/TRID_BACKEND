import struct
from fastapi import UploadFile, HTTPException, status

ALLOWED_EXTENSIONS = {".stl", ".obj", ".step", ".stp"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def validate_extension(filename: str) -> str:
    name = filename.lower()
    for ext in ALLOWED_EXTENSIONS:
        if name.endswith(ext):
            return ext
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
    )


def validate_file_size(size: int):
    if size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded.",
        )
    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max allowed: {MAX_FILE_SIZE // (1024*1024)} MB",
        )


def validate_stl(data: bytes) -> bool:
    if len(data) < 84:
        return False
    # Binary STL: header(80) + triangle_count(4) + triangles(50 each)
    triangle_count = struct.unpack_from("<I", data, 80)[0]
    expected_size = 84 + triangle_count * 50
    if abs(len(data) - expected_size) < 10:
        return True
    # ASCII STL
    try:
        text = data[:256].decode("utf-8", errors="ignore").strip().lower()
        return text.startswith("solid")
    except Exception:
        return False


def validate_obj(data: bytes) -> bool:
    try:
        text = data[:512].decode("utf-8", errors="ignore")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("v ", "vn ", "vt ", "f ", "#")):
                return True
        return False
    except Exception:
        return False


def validate_step(data: bytes) -> bool:
    try:
        text = data[:256].decode("utf-8", errors="ignore").upper()
        return "ISO-10303" in text or "STEP" in text or "FILE_DESCRIPTION" in text
    except Exception:
        return False


def validate_geometry(data: bytes, extension: str) -> bool:
    validators = {
        ".stl": validate_stl,
        ".obj": validate_obj,
        ".step": validate_step,
        ".stp": validate_step,
    }
    validator = validators.get(extension)
    if validator is None:
        return False
    return validator(data)
