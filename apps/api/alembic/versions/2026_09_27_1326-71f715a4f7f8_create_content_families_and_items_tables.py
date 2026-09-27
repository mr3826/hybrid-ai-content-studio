"""create_content_families_and_items_tables

Revision ID: 71f715a4f7f8
Revises: 06ce8181cc9b
Create Date: 2026-09-27 13:26:26.519176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71f715a4f7f8'
down_revision: Union[str, None] = '06ce8181cc9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create content_families table
    op.create_table(
        'content_families',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('slug', sa.String(length=256), nullable=False),
        sa.Column('topic_id', sa.String(length=36), nullable=True),
        sa.Column('research_packet_id', sa.String(length=36), nullable=True),
        sa.Column('originality_plan_id', sa.String(length=36), nullable=True),
        sa.Column('primary_experiment_id', sa.String(length=36), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='DRAFT', nullable=False),
        sa.Column('content_pillar', sa.String(length=128), server_default='Core', nullable=False),
        sa.Column('original_value_type', sa.String(length=64), server_default='benchmark', nullable=False),
        sa.Column('summary', sa.Text(), server_default='', nullable=False),
        sa.Column('research_cost', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('experiment_cost', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('ai_cost', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('media_cost', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('manual_time_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('local_compute_seconds', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['topic_id'], ['opportunities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['research_packet_id'], ['research_packets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['originality_plan_id'], ['originality_plans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['primary_experiment_id'], ['experiments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('content_families', schema=None) as batch_op:
        batch_op.create_index('ix_content_families_slug', ['slug'], unique=True)
        batch_op.create_index('ix_content_families_status', ['status'], unique=False)
        batch_op.create_index('ix_content_families_topic_id', ['topic_id'], unique=False)
        batch_op.create_index('ix_content_families_research_packet_id', ['research_packet_id'], unique=False)
        batch_op.create_index('ix_content_families_originality_plan_id', ['originality_plan_id'], unique=False)
        batch_op.create_index('ix_content_families_primary_experiment_id', ['primary_experiment_id'], unique=False)

    # 2. Create content_items table
    op.create_table(
        'content_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('content_family_id', sa.String(length=36), nullable=False),
        sa.Column('format', sa.String(length=32), nullable=False),
        sa.Column('platform_target', sa.String(length=32), server_default='youtube', nullable=False),
        sa.Column('working_title', sa.String(length=256), nullable=False),
        sa.Column('angle', sa.Text(), nullable=False),
        sa.Column('hook_type', sa.String(length=64), server_default='bold_claim', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='PLANNED', nullable=False),
        sa.Column('script_version_id', sa.String(length=64), nullable=True),
        sa.Column('metadata_version_id', sa.String(length=64), nullable=True),
        sa.Column('incremental_cost', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('manual_time_minutes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('local_compute_seconds', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('original_value_connection', sa.Text(), server_default='', nullable=False),
        sa.Column('viewer_value', sa.Text(), server_default='', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['content_family_id'], ['content_families.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('content_items', schema=None) as batch_op:
        batch_op.create_index('ix_content_items_content_family_id', ['content_family_id'], unique=False)
        batch_op.create_index('ix_content_items_status', ['status'], unique=False)

    # 3. Create content_item_evidence_selections table
    op.create_table(
        'content_item_evidence_selections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('content_item_id', sa.String(length=36), nullable=False),
        sa.Column('claim_id', sa.String(length=36), nullable=False),
        sa.Column('relevance_note', sa.Text(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('content_item_evidence_selections', schema=None) as batch_op:
        batch_op.create_index('ix_content_item_evidence_selections_content_item_id', ['content_item_id'], unique=False)
        batch_op.create_index('ix_content_item_evidence_selections_claim_id', ['claim_id'], unique=False)


def downgrade() -> None:
    op.drop_table('content_item_evidence_selections')
    op.drop_table('content_items')
    op.drop_table('content_families')
