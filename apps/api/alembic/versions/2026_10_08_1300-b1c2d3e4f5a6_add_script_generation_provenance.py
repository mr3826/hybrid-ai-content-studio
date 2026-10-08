"""add_script_generation_provenance

Revision ID: b1c2d3e4f5a6
Revises: 9c0d1e2f3a4b
Create Date: 2026-10-08 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "9c0d1e2f3a4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scripts", sa.Column("generation_metadata", sa.JSON(), nullable=True))
    op.add_column(
        "script_sections",
        sa.Column(
            "evidence_category",
            sa.String(length=32),
            server_default="context",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("script_sections", "evidence_category")
    op.drop_column("scripts", "generation_metadata")
