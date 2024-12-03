"""Add first_level_channel_id to users

Revision ID: 101dbfabc1a4
Revises: 0ada641e0b86
Create Date: 2024-11-28 18:17:36.900661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '101dbfabc1a4'
down_revision: Union[str, None] = '0ada641e0b86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the 'first_level_channel_id' column to the 'users' table
    op.add_column('users', sa.Column('first_level_channel_id', sa.Integer(), nullable=True))

def downgrade() -> None:
    # Drop the 'first_level_channel_id' column in case we need to roll back the migration
    op.drop_column('users', 'first_level_channel_id')
