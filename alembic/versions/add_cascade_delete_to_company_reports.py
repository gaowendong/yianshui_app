"""add cascade delete to company reports

Revision ID: 7a9c4d2e1f3b
Revises: remove_tax_number_unique
Create Date: 2024-01-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '7a9c4d2e1f3b'
down_revision = 'remove_tax_number_unique'
branch_labels = None
depends_on = None

def upgrade():
    # First drop the existing foreign key
    op.drop_constraint('company_reports_ibfk_1', 'company_reports', type_='foreignkey')
    
    # Re-create the foreign key with ON DELETE CASCADE
    op.create_foreign_key(
        'company_reports_ibfk_1',
        'company_reports',
        'company_info',
        ['company_tax_number'],
        ['tax_number'],
        ondelete='CASCADE'
    )

def downgrade():
    # Drop the CASCADE foreign key
    op.drop_constraint('company_reports_ibfk_1', 'company_reports', type_='foreignkey')
    
    # Re-create the original foreign key without CASCADE
    op.create_foreign_key(
        'company_reports_ibfk_1',
        'company_reports',
        'company_info',
        ['company_tax_number'],
        ['tax_number']
    )
