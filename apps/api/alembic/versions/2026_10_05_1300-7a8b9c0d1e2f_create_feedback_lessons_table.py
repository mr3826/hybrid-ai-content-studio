"""create_feedback_lessons_table

Revision ID: 7a8b9c0d1e2f
Revises: 6f7a8b9c0d1e
Create Date: 2026-10-05 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, None] = '6f7a8b9c0d1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'feedback_lessons' not in tables:
        op.create_table(
            'feedback_lessons',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('content_item_id', sa.String(length=36), nullable=True),
            sa.Column('lesson_type', sa.String(length=64), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('observation', sa.Text(), nullable=False),
            sa.Column('impact_level', sa.String(length=32), server_default='MEDIUM', nullable=False),
            sa.Column('confidence_score', sa.Float(), server_default='0.8', nullable=False),
            sa.Column('evidence_data', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('proposed_adjustment', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
            sa.Column('creator_notes', sa.Text(), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_feedback_lessons_content_item_id'), 'feedback_lessons', ['content_item_id'], unique=False)
        op.create_index(op.f('ix_feedback_lessons_lesson_type'), 'feedback_lessons', ['lesson_type'], unique=False)
        op.create_index(op.f('ix_feedback_lessons_status'), 'feedback_lessons', ['status'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'feedback_lessons' in tables:
        op.drop_index(op.f('ix_feedback_lessons_status'), table_name='feedback_lessons')
        op.drop_index(op.f('ix_feedback_lessons_lesson_type'), table_name='feedback_lessons')
        op.drop_index(op.f('ix_feedback_lessons_content_item_id'), table_name='feedback_lessons')
        op.drop_table('feedback_lessons')
