"""merge multiple heads

Revision ID: b8031aa5a849
Revises: f64d50a9274f, remove_channel_rel
Create Date: 2024-12-10 13:18:50.138174

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8031aa5a849'
down_revision: Union[str, None] = ('f64d50a9274f', 'remove_channel_rel')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
