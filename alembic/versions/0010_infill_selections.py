"""create infill_selections table

Revision ID: 0010_infill_selections
Revises: 0009_use_cases
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0010_infill_selections"
down_revision = "0009_use_cases"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "infill_selections",
        sa.Column("id",                       UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id",                 sa.String(64), sa.ForeignKey("uploaded_models.model_id"), nullable=False),
        sa.Column("material_slug",            sa.String(64), nullable=False),
        sa.Column("infill_profile",           sa.String(16), nullable=False),
        sa.Column("infill_percentage",        sa.Integer(),  nullable=False),
        sa.Column("infill_factor",            sa.Float(),    nullable=False),
        sa.Column("model_volume",             sa.Float(),    nullable=False),
        sa.Column("effective_model_material", sa.Float(),    nullable=False),
        sa.Column("is_resin",                 sa.Boolean(),  nullable=False, server_default="false"),
        sa.Column("created_at",               sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",               sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_infill_selections_model_id", "infill_selections", ["model_id"])


def downgrade():
    op.drop_index("ix_infill_selections_model_id", table_name="infill_selections")
    op.drop_table("infill_selections")
