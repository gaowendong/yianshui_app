"""add_channel_admin_and_company_info_channel_relationship

Revision ID: 8d2e08f2c7fa
Revises: 8ae517d07485
Create Date: 2024-12-09 10:28:17.441436

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d2e08f2c7fa'
down_revision: Union[str, None] = '8ae517d07485'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(None, 'channels', 'users', ['channel_admin_id'], ['id'])
    op.create_foreign_key(None, 'company_info', 'channels', ['channel_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'company_info', type_='foreignkey')
    op.drop_constraint(None, 'channels', type_='foreignkey')
    # ### end Alembic commands ###
