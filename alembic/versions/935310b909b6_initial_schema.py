"""initial schema: ticket.resolved_by and ticket.escalated_at

Revision ID: 935310b909b6
Revises:
Create Date: 2026-10-04 09:33:57.243227

Baseline for the existing database. Columns are added only if missing so this
works both on the current DB (where they already exist) and on older copies.

- resolved_by:  'ai' or the slack_id of the person who resolved the ticket.
                No FK because 'ai' is not a user_details row; instead a CHECK
                ensures it is only set on resolved tickets.
- escalated_at: last time the SLA job escalated the ticket (NULL = never).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '935310b909b6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RESOLVED_BY_CHECK = 'ck_ticket_resolved_by_requires_resolved'


def _ticket_columns() -> set[str]:
    return {c['name'] for c in sa.inspect(op.get_bind()).get_columns('ticket')}


def upgrade() -> None:
    """Upgrade schema."""
    columns = _ticket_columns()

    if 'resolved_by' not in columns:
        op.add_column('ticket', sa.Column('resolved_by', sa.String(length=50), nullable=True))
    if 'escalated_at' not in columns:
        op.add_column('ticket', sa.Column('escalated_at', sa.DateTime(), nullable=True))

    op.create_check_constraint(
        RESOLVED_BY_CHECK,
        'ticket',
        "resolved_by IS NULL OR status = 'resolved'",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(RESOLVED_BY_CHECK, 'ticket', type_='check')
    op.drop_column('ticket', 'escalated_at')
    op.drop_column('ticket', 'resolved_by')
