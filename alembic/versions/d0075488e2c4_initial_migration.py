"""initial_migration

Revision ID: d0075488e2c4
Revises: 
Create Date: 2024-12-05 10:21:02.134070

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'd0075488e2c4'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('email', sa.String(225), nullable=True),
        sa.Column('username', sa.String(225), nullable=True),
        sa.Column('password', sa.String(225), nullable=True),
        sa.Column('firstname', sa.String(225), nullable=True),
        sa.Column('lastname', sa.String(225), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.Column('role', sa.String(225), nullable=True),
        sa.Column('first_level_channel_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['first_level_channel_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create company_info table
    op.create_table('company_info',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('company_name', sa.String(225), nullable=True),
        sa.Column('tax_number', sa.String(225), nullable=False),
        sa.Column('post_data', sa.String(225), nullable=True),
        sa.Column('post_initiator_user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Boolean(), nullable=True),
        sa.Column('query_result', sa.String(225), nullable=True),
        sa.ForeignKeyConstraint(['post_initiator_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tax_number', name='uix_tax_number')
    )
    op.create_index('ix_company_info_company_name', 'company_info', ['company_name'])
    op.create_index('ix_company_info_tax_number', 'company_info', ['tax_number'], unique=True)

    # Create risk_reports table
    op.create_table('risk_reports',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create query_results table
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

    # Create company_reports table
    op.create_table('company_reports',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company_tax_number', sa.String(225), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=True),
        sa.Column('quarter', sa.Integer(), nullable=True),
        sa.Column('report_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['company_tax_number'], ['company_info.tax_number'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('company_reports')
    op.drop_table('query_results')
    op.drop_table('risk_reports')
    op.drop_index('ix_company_info_tax_number', table_name='company_info')
    op.drop_index('ix_company_info_company_name', table_name='company_info')
    op.drop_table('company_info')
    op.drop_table('users')
