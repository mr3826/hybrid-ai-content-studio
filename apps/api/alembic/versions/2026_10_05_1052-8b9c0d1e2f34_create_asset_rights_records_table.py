"""create_asset_rights_records_table

Revision ID: 8b9c0d1e2f34
Revises: 6a7f8e9d0123
Create Date: 2026-10-05 10:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b9c0d1e2f34'
down_revision: Union[str, None] = '6a7f8e9d0123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'asset_rights_records' not in tables:
        op.create_table(
            'asset_rights_records',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('content_item_id', sa.String(length=36), nullable=True),
            sa.Column('title', sa.String(length=256), nullable=False),
            sa.Column('asset_type', sa.String(length=64), server_default='image', nullable=False),
            sa.Column('uri', sa.String(length=512), nullable=True),
            sa.Column('source', sa.String(length=256), nullable=False),
            sa.Column('creator_provider', sa.String(length=256), nullable=True),
            sa.Column('license_type', sa.String(length=128), server_default='Unknown', nullable=False),
            sa.Column('commercial_use_status', sa.String(length=32), server_default='UNKNOWN', nullable=False),
            sa.Column('attribution_required', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('attribution_text', sa.Text(), nullable=True),
            sa.Column('license_proof', sa.Text(), nullable=True),
            sa.Column('expiry_date', sa.String(length=64), nullable=True),
            sa.Column('is_ai_generated', sa.Boolean(), server_default='0', nullable=False),
            sa.Column('ai_tool', sa.String(length=128), nullable=True),
            sa.Column('status', sa.String(length=32), server_default='UNKNOWN', nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('extra_metadata', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_asset_rights_records_content_item_id'), 'asset_rights_records', ['content_item_id'], unique=False)
        op.create_index(op.f('ix_asset_rights_records_asset_type'), 'asset_rights_records', ['asset_type'], unique=False)
        op.create_index(op.f('ix_asset_rights_records_status'), 'asset_rights_records', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_asset_rights_records_status'), table_name='asset_rights_records')
    op.drop_index(op.f('ix_asset_rights_records_asset_type'), table_name='asset_rights_records')
    op.drop_index(op.f('ix_asset_rights_records_content_item_id'), table_name='asset_rights_records')
    op.drop_table('asset_rights_records')
