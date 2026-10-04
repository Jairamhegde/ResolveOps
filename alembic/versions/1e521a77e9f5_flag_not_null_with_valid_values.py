"""flag not null with valid values

Revision ID: 1e521a77e9f5
Revises: cd647f44f7d5
Create Date: 2026-10-04

ticket.flag becomes NOT NULL (default 'none') and is limited to the values of
backend.schemas.Flag. Existing NULL flags are backfilled to 'none'.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e521a77e9f5'
down_revision: Union[str, Sequence[str], None] = 'cd647f44f7d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAG_CHECK = 'ck_ticket_flag_valid'
# Spelled out rather than imported, so this migration doesn't change if the enum does
FLAG_VALUES = ('none', 'unclear', 'spam', 'injection', 'ai_failed')


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE ticket SET flag = 'none' WHERE flag IS NULL")
    op.alter_column('ticket', 'flag',
               existing_type=sa.String(length=50),
               nullable=False,
               server_default=sa.text("'none'"))
    op.create_check_constraint(
        FLAG_CHECK,
        'ticket',
        "flag IN (" + ", ".join(f"'{v}'" for v in FLAG_VALUES) + ")",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(FLAG_CHECK, 'ticket', type_='check')
    op.alter_column('ticket', 'flag',
               existing_type=sa.String(length=50),
               nullable=True,
               server_default=None)
