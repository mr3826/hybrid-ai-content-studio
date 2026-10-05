"""create_quality_gate_audits_table

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-10-05 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e6f7a8b9c0d'
down_revision: Union[str, None] = '4d5e6f7a8b9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'quality_gate_audits' not in tables:
        op.create_table(
            'quality_gate_audits',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('content_item_id', sa.String(length=36), nullable=False),
            sa.Column('script_id', sa.String(length=36), nullable=True),
            sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
            sa.Column('overall_score', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('evidence_quality', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('brand_fit', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('originality', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('viewer_value', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('niche_fit', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('repetition_intelligence', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('asset_rights', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('media_qc', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('estimated_cost', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('actionable_recommendations', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('is_approved', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('approved_by', sa.String(length=128), nullable=True),
            sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('override_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_quality_gate_audits_content_item_id'), 'quality_gate_audits', ['content_item_id'], unique=False)
        op.create_index(op.f('ix_quality_gate_audits_script_id'), 'quality_gate_audits', ['script_id'], unique=False)
        op.create_index(op.f('ix_quality_gate_audits_status'), 'quality_gate_audits', ['status'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'quality_gate_audits' in tables:
        op.drop_index(op.f('ix_quality_gate_audits_status'), table_name='quality_gate_audits')
        op.drop_index(op.f('ix_quality_gate_audits_script_id'), table_name='quality_gate_audits')
        op.drop_index(op.f('ix_quality_gate_audits_content_item_id'), table_name='quality_gate_audits')
        op.drop_table('quality_gate_audits')
