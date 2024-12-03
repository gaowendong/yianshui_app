"""test migration

Revision ID: 5be0592cd9e0
Revises: 101dbfabc1a4
Create Date: 2024-11-28 18:27:00.096655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5be0592cd9e0'
down_revision: Union[str, None] = '101dbfabc1a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
