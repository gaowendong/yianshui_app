"""update cascade delete relationships

Revision ID: 5dd464aa11bb
Revises: 7a9c4d2e1f3b
Create Date: 2024-12-05 18:07:09.750278

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dd464aa11bb'
down_revision: Union[str, None] = '7a9c4d2e1f3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_foreign_key(None, 'company_reports', 'users', ['user_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'company_reports', type_='foreignkey')
    # ### end Alembic commands ###
