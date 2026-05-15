"""create materials table

Revision ID: 0008_materials
Revises: 0007_material_families
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0008_materials"
down_revision = "0007_material_families"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "materials",
        sa.Column("id",                     UUID(as_uuid=True), primary_key=True),
        sa.Column("family_id",              UUID(as_uuid=True), sa.ForeignKey("material_families.id"), nullable=False),
        sa.Column("name",                   sa.String(64),  unique=True, nullable=False),
        sa.Column("slug",                   sa.String(64),  unique=True, nullable=False),
        sa.Column("short_description",      sa.String(512), nullable=True),
        sa.Column("price_per_cc",           sa.Float(),     nullable=False),
        sa.Column("strength_category",      sa.String(32),  nullable=False),
        sa.Column("flexibility_category",   sa.String(32),  nullable=False),
        sa.Column("outdoor_suitable",       sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("heat_resistance",        sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("supports_infill",        sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("default_support_density",sa.String(16),  nullable=False, server_default="normal"),
        sa.Column("tags",                   sa.String(128), nullable=True),
        sa.Column("icon_ref",               sa.String(128), nullable=True),
        sa.Column("sort_order",             sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("is_active",              sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at",             sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",             sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_materials_slug",      "materials", ["slug"])
    op.create_index("ix_materials_family_id", "materials", ["family_id"])
    op.create_index("ix_materials_is_active", "materials", ["is_active"])


def downgrade():
    op.drop_index("ix_materials_is_active", table_name="materials")
    op.drop_index("ix_materials_family_id", table_name="materials")
    op.drop_index("ix_materials_slug",      table_name="materials")
    op.drop_table("materials")
