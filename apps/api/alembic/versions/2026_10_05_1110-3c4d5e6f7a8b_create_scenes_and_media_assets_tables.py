"""create_scenes_and_media_assets_tables

Revision ID: 3c4d5e6f7a8b
Revises: 8b9c0d1e2f34
Create Date: 2026-10-05 11:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c4d5e6f7a8b'
down_revision: Union[str, None] = '8b9c0d1e2f34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. scenes table
    if 'scenes' not in tables:
        op.create_table(
            'scenes',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('script_id', sa.String(length=36), nullable=False),
            sa.Column('section_id', sa.String(length=36), nullable=True),
            sa.Column('scene_order', sa.Integer(), server_default='1', nullable=False),
            sa.Column('narration', sa.Text(), server_default='', nullable=False),
            sa.Column('timing_estimate', sa.Float(), server_default='3.0', nullable=False),
            sa.Column('on_screen_text', sa.Text(), nullable=True),
            sa.Column('visual_type', sa.String(length=64), server_default='real_screen_recording', nullable=False),
            sa.Column('visual_source', sa.String(length=512), nullable=True),
            sa.Column('evidence_reference', sa.String(length=256), nullable=True),
            sa.Column('asset_rights_record_id', sa.String(length=36), nullable=True),
            sa.Column('transition', sa.String(length=32), server_default='cut', nullable=False),
            sa.Column('status', sa.String(length=32), server_default='DRAFT', nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('extra_metadata', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['section_id'], ['script_sections.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['asset_rights_record_id'], ['asset_rights_records.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_scenes_script_id'), 'scenes', ['script_id'], unique=False)
        op.create_index(op.f('ix_scenes_section_id'), 'scenes', ['section_id'], unique=False)
        op.create_index(op.f('ix_scenes_scene_order'), 'scenes', ['scene_order'], unique=False)

    # 2. media_assets table
    if 'media_assets' not in tables:
        op.create_table(
            'media_assets',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('name', sa.String(length=256), nullable=False),
            sa.Column('file_path', sa.String(length=512), nullable=False),
            sa.Column('file_size', sa.Integer(), server_default='0', nullable=False),
            sa.Column('mime_type', sa.String(length=128), server_default='image/png', nullable=False),
            sa.Column('asset_type', sa.String(length=64), server_default='image', nullable=False),
            sa.Column('visual_priority', sa.Integer(), server_default='5', nullable=False),
            sa.Column('tags', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('asset_rights_record_id', sa.String(length=36), nullable=True),
            sa.Column('extra_metadata', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['asset_rights_record_id'], ['asset_rights_records.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade() -> None:
    op.drop_table('media_assets')
    op.drop_index(op.f('ix_scenes_scene_order'), table_name='scenes')
    op.drop_index(op.f('ix_scenes_section_id'), table_name='scenes')
    op.drop_index(op.f('ix_scenes_script_id'), table_name='scenes')
    op.drop_table('scenes')
