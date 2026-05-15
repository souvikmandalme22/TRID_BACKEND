"""create orientation_results table

Revision ID: 0003_orientation_results
Revises: 0002_geometry_analyses
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0003_orientation_results"
down_revision = "0002_geometry_analyses"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "orientation_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id", sa.String(64), sa.ForeignKey("uploaded_models.model_id"), unique=True, nullable=False),
        sa.Column("best_direction_x",  sa.Float(), nullable=False),
        sa.Column("best_direction_y",  sa.Float(), nullable=False),
        sa.Column("best_direction_z",  sa.Float(), nullable=False),
        sa.Column("support_area",      sa.Float(), nullable=False),
        sa.Column("print_height",      sa.Float(), nullable=False),
        sa.Column("bed_stability",     sa.Float(), nullable=False),
        sa.Column("overhang_risk",     sa.Float(), nullable=False),
        sa.Column("orientation_score", sa.Float(), nullable=False),
        sa.Column("n_samples_evaluated", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("analysis_status",   sa.String(32), nullable=False, server_default="pending"),
        sa.Column("error_message",     sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_orientation_results_model_id", "orientation_results", ["model_id"])


def downgrade():
    op.drop_index("ix_orientation_results_model_id", table_name="orientation_results")
    op.drop_table("orientation_results")
