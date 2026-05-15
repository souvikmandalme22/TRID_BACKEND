"""create support_analyses table

Revision ID: 0004_support_analyses
Revises: 0003_orientation_results
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0004_support_analyses"
down_revision = "0003_orientation_results"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "support_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id", sa.String(64), sa.ForeignKey("uploaded_models.model_id"), unique=True, nullable=False),
        sa.Column("raw_support_volume",  sa.Float(), nullable=True),
        sa.Column("support_area",        sa.Float(), nullable=True),
        sa.Column("print_height",        sa.Float(), nullable=True),
        sa.Column("overhang_face_count", sa.Float(), nullable=True),
        sa.Column("analysis_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message",   sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_support_analyses_model_id", "support_analyses", ["model_id"])


def downgrade():
    op.drop_index("ix_support_analyses_model_id", table_name="support_analyses")
    op.drop_table("support_analyses")
