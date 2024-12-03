"""Add role column to User model

Revision ID: 0ada641e0b86
Revises: 51b48ae7e8d3
Create Date: 2024-11-28 18:09:12.900896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '0ada641e0b86'
down_revision: Union[str, None] = '51b48ae7e8d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if column 'role' already exists to prevent error
    if 'role' not in [column['name'] for column in inspect(op.get_bind()).get_columns('users')]:
        op.add_column('users', sa.Column('role', sa.String(225), nullable=True))



def downgrade() -> None:
    pass
