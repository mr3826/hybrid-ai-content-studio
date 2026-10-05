"""create_publication_metrics_snapshots_table

Revision ID: 6f7a8b9c0d1e
Revises: 5e6f7a8b9c0d
Create Date: 2026-10-05 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f7a8b9c0d1e'
down_revision: Union[str, None] = '5e6f7a8b9c0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'publication_metrics_snapshots' not in tables:
        op.create_table(
            'publication_metrics_snapshots',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('content_item_id', sa.String(length=36), nullable=False),
            sa.Column('platform_publication_id', sa.String(length=36), nullable=True),
            sa.Column('platform', sa.String(length=32), nullable=False),
            sa.Column('snapshot_timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.Column('snapshot_label', sa.String(length=64), server_default='24h', nullable=False),
            sa.Column('views', sa.Integer(), server_default='0', nullable=False),
            sa.Column('impressions', sa.Integer(), server_default='0', nullable=False),
            sa.Column('watch_time_seconds', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('average_view_duration_seconds', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('retention_rate_pct', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('hook_retention_3s_pct', sa.Float(), nullable=True),
            sa.Column('hook_retention_30s_pct', sa.Float(), nullable=True),
            sa.Column('likes', sa.Integer(), server_default='0', nullable=False),
            sa.Column('comments', sa.Integer(), server_default='0', nullable=False),
            sa.Column('shares', sa.Integer(), server_default='0', nullable=False),
            sa.Column('saves', sa.Integer(), server_default='0', nullable=False),
            sa.Column('clicks', sa.Integer(), server_default='0', nullable=False),
            sa.Column('subscribers_gained', sa.Integer(), server_default='0', nullable=False),
            sa.Column('revenue_estimated_usd', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('source', sa.String(length=32), server_default='MANUAL', nullable=False),
            sa.Column('raw_metadata', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['platform_publication_id'], ['platform_publications.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_publication_metrics_snapshots_content_item_id'), 'publication_metrics_snapshots', ['content_item_id'], unique=False)
        op.create_index(op.f('ix_publication_metrics_snapshots_platform_publication_id'), 'publication_metrics_snapshots', ['platform_publication_id'], unique=False)
        op.create_index(op.f('ix_publication_metrics_snapshots_platform'), 'publication_metrics_snapshots', ['platform'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'publication_metrics_snapshots' in tables:
        op.drop_index(op.f('ix_publication_metrics_snapshots_platform'), table_name='publication_metrics_snapshots')
        op.drop_index(op.f('ix_publication_metrics_snapshots_platform_publication_id'), table_name='publication_metrics_snapshots')
        op.drop_index(op.f('ix_publication_metrics_snapshots_content_item_id'), table_name='publication_metrics_snapshots')
        op.drop_table('publication_metrics_snapshots')
