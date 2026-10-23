"""add password_hash to user_details

Revision ID: 7c3e1f0a9b2d
Revises: 4b7d2e9a1c3f
Create Date: 2026-10-24

Employees with a password_hash can log in to the dashboard to see their own tickets.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c3e1f0a9b2d'
down_revision: Union[str, Sequence[str], None] = '4b7d2e9a1c3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_details', sa.Column('password_hash', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_details', 'password_hash')
