"""create_cleanup_and_backup_tables

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-10-06 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c0d1e2f3a4b'
down_revision: Union[str, None] = '8b9c0d1e2f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'cleanup_audit_logs' not in tables:
        op.create_table(
            'cleanup_audit_logs',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('run_id', sa.String(length=64), nullable=False),
            sa.Column('mode', sa.String(length=32), server_default='DRY_RUN', nullable=False),
            sa.Column('scanned_files_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('candidate_files_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('deleted_files_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('recovered_bytes', sa.Integer(), server_default='0', nullable=False),
            sa.Column('rules_applied', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('details', sa.JSON(), server_default='[]', nullable=False),
            sa.Column('status', sa.String(length=32), server_default='SUCCESS', nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_cleanup_audit_logs_run_id'), 'cleanup_audit_logs', ['run_id'], unique=False)

    if 'studio_backups' not in tables:
        op.create_table(
            'studio_backups',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('backup_name', sa.String(length=255), nullable=False),
            sa.Column('filepath', sa.String(length=512), nullable=False),
            sa.Column('backup_type', sa.String(length=32), server_default='FULL', nullable=False),
            sa.Column('size_bytes', sa.Integer(), server_default='0', nullable=False),
            sa.Column('checksum_sha256', sa.String(length=64), nullable=False),
            sa.Column('metadata_snapshot', sa.JSON(), server_default='{}', nullable=False),
            sa.Column('status', sa.String(length=32), server_default='AVAILABLE', nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'studio_backups' in tables:
        op.drop_table('studio_backups')

    if 'cleanup_audit_logs' in tables:
        op.drop_index(op.f('ix_cleanup_audit_logs_run_id'), table_name='cleanup_audit_logs')
        op.drop_table('cleanup_audit_logs')
