"""add password_hash to admin

Revision ID: 4b7d2e9a1c3f
Revises: 1e521a77e9f5
Create Date: 2026-10-13

Admins with a password_hash can log in to the dashboard.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4b7d2e9a1c3f'
down_revision: Union[str, Sequence[str], None] = '1e521a77e9f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('admin', sa.Column('password_hash', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('admin', 'password_hash')
