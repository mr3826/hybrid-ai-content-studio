"""create_export_and_publication_tables

Revision ID: 6a7f8e9d0123
Revises: 54635535316a
Create Date: 2026-09-27 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a7f8e9d0123'
down_revision: Union[str, None] = '54635535316a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. export_packages table
    op.create_table(
        'export_packages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('content_item_id', sa.String(length=36), nullable=False),
        sa.Column('package_slug', sa.String(length=256), nullable=False),
        sa.Column('export_dir', sa.String(length=512), nullable=False),
        sa.Column('manifest_data', sa.JSON(), nullable=False),
        sa.Column('files', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_export_packages_content_item_id'), 'export_packages', ['content_item_id'], unique=False)

    # 2. platform_publications table
    op.create_table(
        'platform_publications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('content_item_id', sa.String(length=36), nullable=False),
        sa.Column('export_package_id', sa.String(length=36), nullable=True),
        sa.Column('platform', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='NOT_READY', nullable=False),
        sa.Column('title', sa.String(length=256), server_default='', nullable=False),
        sa.Column('caption', sa.Text(), server_default='', nullable=False),
        sa.Column('hashtags', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('pinned_comment', sa.Text(), server_default='', nullable=False),
        sa.Column('checklist', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('post_url', sa.String(length=1024), nullable=True),
        sa.Column('platform_post_id', sa.String(length=128), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['export_package_id'], ['export_packages.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_platform_publications_content_item_id'), 'platform_publications', ['content_item_id'], unique=False)
    op.create_index(op.f('ix_platform_publications_export_package_id'), 'platform_publications', ['export_package_id'], unique=False)
    op.create_index(op.f('ix_platform_publications_status'), 'platform_publications', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_platform_publications_status'), table_name='platform_publications')
    op.drop_index(op.f('ix_platform_publications_export_package_id'), table_name='platform_publications')
    op.drop_index(op.f('ix_platform_publications_content_item_id'), table_name='platform_publications')
    op.drop_table('platform_publications')

    op.drop_index(op.f('ix_export_packages_content_item_id'), table_name='export_packages')
    op.drop_table('export_packages')
