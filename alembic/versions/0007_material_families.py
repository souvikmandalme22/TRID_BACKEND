"""create material_families table

Revision ID: 0007_material_families
Revises: 0006_segments
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0007_material_families"
down_revision = "0006_segments"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "material_families",
        sa.Column("id",          UUID(as_uuid=True), primary_key=True),
        sa.Column("name",        sa.String(64),  unique=True, nullable=False),
        sa.Column("slug",        sa.String(64),  unique=True, nullable=False),
        sa.Column("icon_ref",    sa.String(128), nullable=True),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("sort_order",  sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("is_active",   sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at",  sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_material_families_slug",      "material_families", ["slug"])
    op.create_index("ix_material_families_is_active", "material_families", ["is_active"])

    op.bulk_insert(
        sa.table(
            "material_families",
            sa.column("id",          sa.String),
            sa.column("name",        sa.String),
            sa.column("slug",        sa.String),
            sa.column("icon_ref",    sa.String),
            sa.column("description", sa.String),
            sa.column("sort_order",  sa.Integer),
            sa.column("is_active",   sa.Boolean),
        ),
        [
            {"id": "10000000-0000-0000-0000-000000000001", "name": "Plastic",             "slug": "plastic",             "icon_ref": "icon-plastic",             "description": "Standard plastics for general use prints",               "sort_order": 1, "is_active": True},
            {"id": "10000000-0000-0000-0000-000000000002", "name": "Engineering Plastic", "slug": "engineering-plastic", "icon_ref": "icon-engineering-plastic", "description": "High-strength plastics for functional applications",     "sort_order": 2, "is_active": True},
            {"id": "10000000-0000-0000-0000-000000000003", "name": "Resin",               "slug": "resin",               "icon_ref": "icon-resin",               "description": "High-detail resin for fine and intricate models",         "sort_order": 3, "is_active": True},
            {"id": "10000000-0000-0000-0000-000000000004", "name": "Industrial",          "slug": "industrial",          "icon_ref": "icon-industrial-material", "description": "Industrial-grade materials for heavy-duty applications", "sort_order": 4, "is_active": True},
            {"id": "10000000-0000-0000-0000-000000000005", "name": "Metal",               "slug": "metal",               "icon_ref": "icon-metal",               "description": "Metal materials for structural and premium parts",        "sort_order": 5, "is_active": True},
        ],
    )


def downgrade():
    op.drop_index("ix_material_families_is_active", table_name="material_families")
    op.drop_index("ix_material_families_slug",      table_name="material_families")
    op.drop_table("material_families")
