"""add risk reports table

Revision ID: add_risk_reports_table
Revises: 068dbf7ae0c8
Create Date: 2024-12-03 17:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'add_risk_reports_table'
down_revision = '068dbf7ae0c8'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('risk_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_reports_id'), 'risk_reports', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_risk_reports_id'), table_name='risk_reports')
    op.drop_table('risk_reports')
