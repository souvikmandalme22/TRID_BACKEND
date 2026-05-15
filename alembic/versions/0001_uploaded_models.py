"""create uploaded_models table

Revision ID: 0001_uploaded_models
Revises:
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision = "0001_uploaded_models"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "uploaded_models",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("model_id", sa.String(64), unique=True, nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column(
            "file_type",
            sa.Enum("stl", "obj", "step", "stp", name="filetype"),
            nullable=False,
        ),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column(
            "upload_status",
            sa.Enum("pending", "validated", "processing", "ready", "failed", name="uploadstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_uploaded_models_model_id", "uploaded_models", ["model_id"])
    op.create_index("ix_uploaded_models_upload_status", "uploaded_models", ["upload_status"])
    op.create_index("ix_uploaded_models_created_at", "uploaded_models", ["created_at"])


def downgrade():
    op.drop_index("ix_uploaded_models_created_at", table_name="uploaded_models")
    op.drop_index("ix_uploaded_models_upload_status", table_name="uploaded_models")
    op.drop_index("ix_uploaded_models_model_id", table_name="uploaded_models")
    op.drop_table("uploaded_models")
    op.execute("DROP TYPE IF EXISTS filetype")
    op.execute("DROP TYPE IF EXISTS uploadstatus")
