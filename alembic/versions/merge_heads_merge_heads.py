"""merge heads

Revision ID: merge_heads
Revises: manual_cascade_update, remove_unused_tables
Create Date: 2024-12-05 18:17:47.678011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_heads'
down_revision: Union[str, None] = ('manual_cascade_update', 'remove_unused_tables')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
