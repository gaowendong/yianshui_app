"""remove unused tables

Revision ID: remove_unused_tables
Revises: remove_tax_number_unique
Create Date: 2024-01-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'remove_unused_tables'
down_revision: Union[str, None] = 'remove_tax_number_unique'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop query_results table
    op.drop_table('query_results')
    
    # Drop risk_reports table
    op.drop_table('risk_reports')


def downgrade() -> None:
    # Recreate risk_reports table
    op.create_table('risk_reports',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate query_results table
    op.create_table('query_results',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('company_info_id', sa.Integer(), nullable=True),
        sa.Column('query_data', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.String(225), nullable=True),
        sa.ForeignKeyConstraint(['company_info_id'], ['company_info.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
