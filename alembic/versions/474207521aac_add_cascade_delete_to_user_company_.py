"""add_cascade_delete_to_user_company_reports

Revision ID: 474207521aac
Revises: 8d2e08f2c7fa
Create Date: 2024-12-09 11:07:26.549917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '474207521aac'
down_revision: Union[str, None] = '8d2e08f2c7fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('company_info', 'channel_id',
               existing_type=mysql.INTEGER(),
               nullable=True)
    op.drop_constraint('company_reports_ibfk_2', 'company_reports', type_='foreignkey')
    op.create_foreign_key(None, 'company_reports', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'company_reports', type_='foreignkey')
    op.create_foreign_key('company_reports_ibfk_2', 'company_reports', 'users', ['user_id'], ['id'])
    op.alter_column('company_info', 'channel_id',
               existing_type=mysql.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###