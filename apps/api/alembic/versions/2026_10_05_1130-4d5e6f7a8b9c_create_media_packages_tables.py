"""create_media_packages_tables

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-10-05 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d5e6f7a8b9c'
down_revision: Union[str, None] = '3c4d5e6f7a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. media_packages table
    if 'media_packages' not in tables:
        op.create_table(
            'media_packages',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('script_id', sa.String(length=36), nullable=False),
            sa.Column('content_item_id', sa.String(length=36), nullable=True),
            sa.Column('format', sa.String(length=50), server_default='short_vertical', nullable=False),
            sa.Column('resolution', sa.String(length=20), server_default='1080x1920', nullable=False),
            sa.Column('status', sa.String(length=30), server_default='DRAFT', nullable=False),
            sa.Column('total_duration_sec', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('audio_path', sa.String(length=500), nullable=True),
            sa.Column('subtitle_path', sa.String(length=500), nullable=True),
            sa.Column('video_path', sa.String(length=500), nullable=True),
            sa.Column('timeline_path', sa.String(length=500), nullable=True),
            sa.Column('voice_settings', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('subtitle_settings', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('quality_checks', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['content_item_id'], ['content_items.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_media_packages_script_id'), 'media_packages', ['script_id'], unique=False)
        op.create_index(op.f('ix_media_packages_content_item_id'), 'media_packages', ['content_item_id'], unique=False)
        op.create_index(op.f('ix_media_packages_status'), 'media_packages', ['status'], unique=False)

    # 2. scene_voice_tracks table
    if 'scene_voice_tracks' not in tables:
        op.create_table(
            'scene_voice_tracks',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('media_package_id', sa.String(length=36), nullable=False),
            sa.Column('scene_id', sa.String(length=36), nullable=False),
            sa.Column('audio_path', sa.String(length=500), nullable=False),
            sa.Column('duration_sec', sa.Float(), server_default='0.0', nullable=False),
            sa.Column('word_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('waveform_peaks', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['media_package_id'], ['media_packages.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_scene_voice_tracks_media_package_id'), 'scene_voice_tracks', ['media_package_id'], unique=False)
        op.create_index(op.f('ix_scene_voice_tracks_scene_id'), 'scene_voice_tracks', ['scene_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'scene_voice_tracks' in tables:
        op.drop_index(op.f('ix_scene_voice_tracks_scene_id'), table_name='scene_voice_tracks')
        op.drop_index(op.f('ix_scene_voice_tracks_media_package_id'), table_name='scene_voice_tracks')
        op.drop_table('scene_voice_tracks')

    if 'media_packages' in tables:
        op.drop_index(op.f('ix_media_packages_status'), table_name='media_packages')
        op.drop_index(op.f('ix_media_packages_content_item_id'), table_name='media_packages')
        op.drop_index(op.f('ix_media_packages_script_id'), table_name='media_packages')
        op.drop_table('media_packages')
