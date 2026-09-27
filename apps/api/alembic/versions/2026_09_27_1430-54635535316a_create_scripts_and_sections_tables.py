"""create_scripts_and_sections_tables

Revision ID: 54635535316a
Revises: 71f715a4f7f8
Create Date: 2026-09-27 14:30:04.486051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54635535316a'
down_revision: Union[str, None] = '71f715a4f7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. scripts table
    op.create_table(
        'scripts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('content_item_id', sa.String(length=36), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('format', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column('target_platform', sa.String(length=32), server_default='youtube', nullable=False),
        sa.Column('target_duration_sec', sa.Integer(), server_default='60', nullable=False),
        sa.Column('total_word_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('estimated_duration_sec', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='DRAFT', nullable=False),
        sa.Column('quality_scores', sa.JSON(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('approved_by', sa.String(length=128), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_scripts_content_item_id'), 'scripts', ['content_item_id'], unique=False)
    op.create_index(op.f('ix_scripts_status'), 'scripts', ['status'], unique=False)

    # 2. script_sections table
    op.create_table(
        'script_sections',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('script_id', sa.String(length=36), nullable=False),
        sa.Column('section_type', sa.String(length=32), nullable=False),
        sa.Column('order_index', sa.Integer(), server_default='0', nullable=False),
        sa.Column('heading', sa.String(length=128), server_default='', nullable=False),
        sa.Column('narration', sa.Text(), server_default='', nullable=False),
        sa.Column('visual_cue', sa.Text(), server_default='', nullable=False),
        sa.Column('estimated_seconds', sa.Integer(), server_default='0', nullable=False),
        sa.Column('word_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('linked_claim_ids', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_script_sections_script_id'), 'script_sections', ['script_id'], unique=False)

    # 3. script_revisions table
    op.create_table(
        'script_revisions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('script_id', sa.String(length=36), nullable=False),
        sa.Column('section_id', sa.String(length=36), nullable=True),
        sa.Column('revision_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('trigger', sa.String(length=64), nullable=False),
        sa.Column('notes', sa.Text(), server_default='', nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_script_revisions_script_id'), 'script_revisions', ['script_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_script_revisions_script_id'), table_name='script_revisions')
    op.drop_table('script_revisions')

    op.drop_index(op.f('ix_script_sections_script_id'), table_name='script_sections')
    op.drop_table('script_sections')

    op.drop_index(op.f('ix_scripts_status'), table_name='scripts')
    op.drop_index(op.f('ix_scripts_content_item_id'), table_name='scripts')
    op.drop_table('scripts')
