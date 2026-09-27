"""retrofit_job_queue_and_engine_versioning

Revision ID: 7b8e1a34d2c9
Revises: 015e647e5750
Create Date: 2026-09-27 06:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b8e1a34d2c9'
down_revision: Union[str, None] = '015e647e5750'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create studio_jobs table for SQLite-backed job queue
    op.create_table(
        'studio_jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_type', sa.String(length=64), nullable=False),
        sa.Column('engine_id', sa.String(length=64), nullable=True),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('result', sa.JSON(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('studio_jobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_studio_jobs_job_type'), ['job_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_studio_jobs_engine_id'), ['engine_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_studio_jobs_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_studio_jobs_status'), ['status'], unique=False)

    # 2. Add rules_version and project_id to engine_runs
    with op.batch_alter_table('engine_runs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rules_version', sa.String(length=32), server_default='1.0.0', nullable=False))
        batch_op.add_column(sa.Column('project_id', sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f('ix_engine_runs_project_id'), ['project_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('engine_runs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_engine_runs_project_id'))
        batch_op.drop_column('project_id')
        batch_op.drop_column('rules_version')

    with op.batch_alter_table('studio_jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_studio_jobs_status'))
        batch_op.drop_index(batch_op.f('ix_studio_jobs_project_id'))
        batch_op.drop_index(batch_op.f('ix_studio_jobs_engine_id'))
        batch_op.drop_index(batch_op.f('ix_studio_jobs_job_type'))

    op.drop_table('studio_jobs')
