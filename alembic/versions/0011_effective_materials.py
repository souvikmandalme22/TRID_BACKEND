"""create effective_materials table

Revision ID: 0011_effective_materials
Revises: 0010_infill_selections
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0011_effective_materials"
down_revision = "0010_infill_selections"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "effective_materials",
        sa.Column("id",                        UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id",                  sa.String(64), sa.ForeignKey("uploaded_models.model_id"), nullable=False),
        sa.Column("material_slug",             sa.String(64), nullable=False),
        sa.Column("model_volume",              sa.Float(), nullable=False),
        sa.Column("infill_factor",             sa.Float(), nullable=False),
        sa.Column("effective_model_material",  sa.Float(), nullable=False),
        sa.Column("raw_support_volume",        sa.Float(), nullable=False),
        sa.Column("support_density_factor",    sa.Float(), nullable=False),
        sa.Column("effective_support_material",sa.Float(), nullable=False),
        sa.Column("final_effective_material",  sa.Float(), nullable=False),
        sa.Column("is_resin",                  sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at",                sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",                sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_effective_materials_model_id", "effective_materials", ["model_id"])


def downgrade():
    op.drop_index("ix_effective_materials_model_id", table_name="effective_materials")
    op.drop_table("effective_materials")
