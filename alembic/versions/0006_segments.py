"""create segments table

Revision ID: 0006_segments
Revises: 0005_support_density_results
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0006_segments"
down_revision = "0005_support_density_results"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "segments",
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
    op.create_index("ix_segments_slug",      "segments", ["slug"])
    op.create_index("ix_segments_is_active", "segments", ["is_active"])

    # Seed default segments
    op.bulk_insert(
        sa.table(
            "segments",
            sa.column("id",          sa.String),
            sa.column("name",        sa.String),
            sa.column("slug",        sa.String),
            sa.column("icon_ref",    sa.String),
            sa.column("description", sa.String),
            sa.column("sort_order",  sa.Integer),
            sa.column("is_active",   sa.Boolean),
        ),
        [
            {"id": "00000000-0000-0000-0000-000000000001", "name": "Engineering",  "slug": "engineering",  "icon_ref": "icon-engineering",  "description": "Functional parts, prototypes, mechanical components", "sort_order": 1, "is_active": True},
            {"id": "00000000-0000-0000-0000-000000000002", "name": "Automotive",   "slug": "automotive",   "icon_ref": "icon-automotive",   "description": "Car parts, brackets, custom automotive components",  "sort_order": 2, "is_active": True},
            {"id": "00000000-0000-0000-0000-000000000003", "name": "Medical",      "slug": "medical",      "icon_ref": "icon-medical",      "description": "Medical devices, prosthetics, surgical tools",       "sort_order": 3, "is_active": True},
            {"id": "00000000-0000-0000-0000-000000000004", "name": "Jewelry",      "slug": "jewelry",      "icon_ref": "icon-jewelry",      "description": "Rings, pendants, intricate decorative pieces",       "sort_order": 4, "is_active": True},
            {"id": "00000000-0000-0000-0000-000000000005", "name": "Industrial",   "slug": "industrial",   "icon_ref": "icon-industrial",   "description": "Heavy-duty industrial parts and tooling",            "sort_order": 5, "is_active": True},
            {"id": "00000000-0000-0000-0000-000000000006", "name": "Consumer",     "slug": "consumer",     "icon_ref": "icon-consumer",     "description": "Everyday consumer products and gadgets",             "sort_order": 6, "is_active": True},
            {"id": "00000000-0000-0000-0000-000000000007", "name": "Robotics",     "slug": "robotics",     "icon_ref": "icon-robotics",     "description": "Robot parts, mounts, servo housings",               "sort_order": 7, "is_active": True},
            {"id": "00000000-0000-0000-0000-000000000008", "name": "Architecture", "slug": "architecture", "icon_ref": "icon-architecture", "description": "Architectural models and structural prototypes",     "sort_order": 8, "is_active": True},
        ],
    )


def downgrade():
    op.drop_index("ix_segments_is_active", table_name="segments")
    op.drop_index("ix_segments_slug",      table_name="segments")
    op.drop_table("segments")
