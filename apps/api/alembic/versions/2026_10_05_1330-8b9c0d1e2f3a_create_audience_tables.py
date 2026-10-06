"""create_audience_tables

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-10-05 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b9c0d1e2f3a'
down_revision: Union[str, None] = '7a8b9c0d1e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'lead_magnets' not in tables:
        op.create_table(
            'lead_magnets',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('slug', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('magnet_type', sa.String(length=64), server_default='cheat_sheet', nullable=False),
            sa.Column('landing_page_url', sa.String(length=512), nullable=False),
            sa.Column('cta_copy', sa.Text(), nullable=False),
            sa.Column('status', sa.String(length=32), server_default='ACTIVE', nullable=False),
            sa.Column('target_pillar', sa.String(length=128), server_default='Core', nullable=False),
            sa.Column('estimated_value_usd', sa.Float(), server_default='15.0', nullable=False),
            sa.Column('total_downloads', sa.Integer(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_lead_magnets_slug'), 'lead_magnets', ['slug'], unique=True)
        op.create_index(op.f('ix_lead_magnets_status'), 'lead_magnets', ['status'], unique=False)

    if 'audience_conversions' not in tables:
        op.create_table(
            'audience_conversions',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('lead_magnet_id', sa.String(length=36), nullable=True),
            sa.Column('content_item_id', sa.String(length=36), nullable=True),
            sa.Column('platform', sa.String(length=32), nullable=False),
            sa.Column('utm_source', sa.String(length=128), nullable=True),
            sa.Column('utm_medium', sa.String(length=128), nullable=True),
            sa.Column('utm_campaign', sa.String(length=128), nullable=True),
            sa.Column('conversion_timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('clicks', sa.Integer(), server_default='0', nullable=False),
            sa.Column('signups', sa.Integer(), server_default='0', nullable=False),
            sa.Column('customers', sa.Integer(), server_default='0', nullable=False),
            sa.Column('revenue_usd', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('source', sa.String(length=32), server_default='MANUAL', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['lead_magnet_id'], ['lead_magnets.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_audience_conversions_content_item_id'), 'audience_conversions', ['content_item_id'], unique=False)
        op.create_index(op.f('ix_audience_conversions_lead_magnet_id'), 'audience_conversions', ['lead_magnet_id'], unique=False)
        op.create_index(op.f('ix_audience_conversions_platform'), 'audience_conversions', ['platform'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'audience_conversions' in tables:
        op.drop_index(op.f('ix_audience_conversions_platform'), table_name='audience_conversions')
        op.drop_index(op.f('ix_audience_conversions_lead_magnet_id'), table_name='audience_conversions')
        op.drop_index(op.f('ix_audience_conversions_content_item_id'), table_name='audience_conversions')
        op.drop_table('audience_conversions')

    if 'lead_magnets' in tables:
        op.drop_index(op.f('ix_lead_magnets_status'), table_name='lead_magnets')
        op.drop_index(op.f('ix_lead_magnets_slug'), table_name='lead_magnets')
        op.drop_table('lead_magnets')
