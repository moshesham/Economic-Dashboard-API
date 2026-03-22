"""add_incremental_ingestion_watermarks

Revision ID: a1b2c3d4e5f6
Revises: c24c9bbafea3
Create Date: 2026-03-19 00:00:00.000000

Adds the data_ingestion_watermarks table that tracks the high-water mark
(last successfully fetched date) for each (source, series_key) pair so
incremental data refreshes only pull records newer than the stored date.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c24c9bbafea3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'data_ingestion_watermarks',
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('series_key', sa.String(), nullable=False),
        sa.Column('last_fetched_date', sa.Date(), nullable=False),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('records_fetched', sa.Integer(), nullable=True, default=0),
        sa.Column('status', sa.String(), nullable=True, default='ok'),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('source', 'series_key'),
    )
    op.create_index(
        'idx_watermark_source',
        'data_ingestion_watermarks',
        ['source'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('idx_watermark_source', table_name='data_ingestion_watermarks')
    op.drop_table('data_ingestion_watermarks')
