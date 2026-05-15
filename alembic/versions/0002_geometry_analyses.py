"""create geometry_analyses table

Revision ID: 0002_geometry_analyses
Revises: 0001_uploaded_models
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0002_geometry_analyses"
down_revision = "0001_uploaded_models"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "geometry_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id", sa.String(64), sa.ForeignKey("uploaded_models.model_id"), unique=True, nullable=False),
        sa.Column("dim_x", sa.Float(), nullable=True),
        sa.Column("dim_y", sa.Float(), nullable=True),
        sa.Column("dim_z", sa.Float(), nullable=True),
        sa.Column("bbox_min_x", sa.Float(), nullable=True),
        sa.Column("bbox_min_y", sa.Float(), nullable=True),
        sa.Column("bbox_min_z", sa.Float(), nullable=True),
        sa.Column("bbox_max_x", sa.Float(), nullable=True),
        sa.Column("bbox_max_y", sa.Float(), nullable=True),
        sa.Column("bbox_max_z", sa.Float(), nullable=True),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.Column("surface_area", sa.Float(), nullable=True),
        sa.Column("is_watertight", sa.Boolean(), nullable=True),
        sa.Column("analysis_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_geometry_analyses_model_id", "geometry_analyses", ["model_id"])


def downgrade():
    op.drop_index("ix_geometry_analyses_model_id", table_name="geometry_analyses")
    op.drop_table("geometry_analyses")
