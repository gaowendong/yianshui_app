"""add company info fields

Revision ID: add_company_info_fields
Revises: merge_heads
Create Date: 2024-01-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import JSON

# revision identifiers, used by Alembic.
revision = 'add_company_info_fields'
down_revision = 'merge_heads'
branch_labels = None
depends_on = None


def upgrade():
    # Add only the missing columns
    op.add_column('company_info', sa.Column('uploaded_files', JSON, nullable=True))
    op.add_column('company_info', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True))


def downgrade():
    # Remove the new columns
    op.drop_column('company_info', 'uploaded_files')
    op.drop_column('company_info', 'created_at')
