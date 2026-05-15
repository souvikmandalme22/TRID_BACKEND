"""create use_cases table

Revision ID: 0009_use_cases
Revises: 0008_materials
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0009_use_cases"
down_revision = "0008_materials"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "use_cases",
        sa.Column("id",                   UUID(as_uuid=True), primary_key=True),
        sa.Column("name",                 sa.String(64),  unique=True, nullable=False),
        sa.Column("slug",                 sa.String(64),  unique=True, nullable=False),
        sa.Column("description",          sa.String(512), nullable=True),
        sa.Column("durability_level",     sa.String(32),  nullable=False),
        sa.Column("recommended_strength", sa.String(32),  nullable=False),
        sa.Column("sort_order",           sa.Integer(),   nullable=False, server_default="0"),
        sa.Column("is_active",            sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at",           sa.DateTime(),  nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",           sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_use_cases_slug",      "use_cases", ["slug"])
    op.create_index("ix_use_cases_is_active", "use_cases", ["is_active"])

    op.bulk_insert(
        sa.table(
            "use_cases",
            sa.column("id",                   sa.String),
            sa.column("name",                 sa.String),
            sa.column("slug",                 sa.String),
            sa.column("description",          sa.String),
            sa.column("durability_level",     sa.String),
            sa.column("recommended_strength", sa.String),
            sa.column("sort_order",           sa.Integer),
            sa.column("is_active",            sa.Boolean),
        ),
        [
            {"id": "20000000-0000-0000-0000-000000000001", "name": "Showpiece",     "slug": "showpiece",    "description": "Decorative display models, not subject to mechanical stress",  "durability_level": "low",     "recommended_strength": "low",    "sort_order": 1, "is_active": True},
            {"id": "20000000-0000-0000-0000-000000000002", "name": "Fit / Assembly","slug": "fit-assembly", "description": "Parts that must fit together with tolerance and precision",    "durability_level": "medium",  "recommended_strength": "medium", "sort_order": 2, "is_active": True},
            {"id": "20000000-0000-0000-0000-000000000003", "name": "Daily Use",     "slug": "daily-use",   "description": "Functional items used regularly under normal conditions",      "durability_level": "high",    "recommended_strength": "high",   "sort_order": 3, "is_active": True},
            {"id": "20000000-0000-0000-0000-000000000004", "name": "Heavy-Duty",    "slug": "heavy-duty",  "description": "Structural or load-bearing parts in demanding environments",  "durability_level": "extreme", "recommended_strength": "ultra",  "sort_order": 4, "is_active": True},
        ],
    )


def downgrade():
    op.drop_index("ix_use_cases_is_active", table_name="use_cases")
    op.drop_index("ix_use_cases_slug",      table_name="use_cases")
    op.drop_table("use_cases")
