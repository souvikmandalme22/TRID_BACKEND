"""create support_density_results table

Revision ID: 0005_support_density_results
Revises: 0004_support_analyses
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0005_support_density_results"
down_revision = "0004_support_analyses"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "support_density_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id", sa.String(64), sa.ForeignKey("uploaded_models.model_id"), nullable=False),
        sa.Column("raw_support_volume",         sa.Float(), nullable=False),
        sa.Column("density_profile",            sa.String(16), nullable=False),
        sa.Column("material_category",          sa.String(16), nullable=False),
        sa.Column("density_factor",             sa.Float(), nullable=False),
        sa.Column("effective_support_material", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_support_density_model_id", "support_density_results", ["model_id"])


def downgrade():
    op.drop_index("ix_support_density_model_id", table_name="support_density_results")
    op.drop_table("support_density_results")
