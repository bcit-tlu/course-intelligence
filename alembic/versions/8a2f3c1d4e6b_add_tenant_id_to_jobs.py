"""add tenant_id to jobs

Revision ID: 8a2f3c1d4e6b
Revises: 074edc6213d0
Create Date: 2026-07-30 10:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8a2f3c1d4e6b'
down_revision: Union[str, Sequence[str], None] = '074edc6213d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('jobs', sa.Column('tenant_id', sa.Text(), nullable=True))
    op.create_index('ix_jobs_tenant_id', 'jobs', ['tenant_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_jobs_tenant_id', table_name='jobs')
    op.drop_column('jobs', 'tenant_id')
