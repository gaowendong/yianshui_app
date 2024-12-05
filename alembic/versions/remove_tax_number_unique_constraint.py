"""remove tax number unique constraint

Revision ID: remove_tax_number_unique
Revises: d0075488e2c4
Create Date: 2024-12-05 13:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_tax_number_unique'
down_revision = 'd0075488e2c4'
branch_labels = None
depends_on = None

def upgrade():
    # First drop the foreign key constraint in company_reports table
    op.drop_constraint('company_reports_ibfk_1', 'company_reports', type_='foreignkey')
    
    # Drop the unique index
    op.drop_index('ix_company_info_tax_number', table_name='company_info')
    
    # Create a new non-unique index
    op.create_index('ix_company_info_tax_number', 'company_info', ['tax_number'])
    
    # Recreate the foreign key constraint without requiring unique
    op.create_foreign_key(
        'company_reports_ibfk_1',
        'company_reports', 'company_info',
        ['company_tax_number'], ['tax_number']
    )

def downgrade():
    # First drop the foreign key constraint
    op.drop_constraint('company_reports_ibfk_1', 'company_reports', type_='foreignkey')
    
    # Drop the non-unique index
    op.drop_index('ix_company_info_tax_number', table_name='company_info')
    
    # Recreate the unique index
    op.create_index('ix_company_info_tax_number', 'company_info', ['tax_number'], unique=True)
    
    # Recreate the foreign key constraint
    op.create_foreign_key(
        'company_reports_ibfk_1',
        'company_reports', 'company_info',
        ['company_tax_number'], ['tax_number']
    )
