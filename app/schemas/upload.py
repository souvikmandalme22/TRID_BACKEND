from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from app.models.upload import UploadStatus, FileType


class UploadResponse(BaseModel):
    id: UUID
    model_id: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_type: FileType
    file_size: int
    upload_status: UploadStatus
    created_at: datetime

    class Config:
        from_attributes = True


class UploadStatusResponse(BaseModel):
    model_id: str
    upload_status: UploadStatus
    file_type: FileType
    file_size: int
    original_filename: str
    created_at: datetime

    class Config:
        from_attributes = True
