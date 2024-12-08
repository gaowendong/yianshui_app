"""manual cascade update

Revision ID: manual_cascade_update
Revises: 5dd464aa11bb
Create Date: 2024-12-05 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'manual_cascade_update'
down_revision = '5dd464aa11bb'
branch_labels = None
depends_on = None

def upgrade():
    # Drop existing foreign keys
    op.drop_constraint('company_reports_ibfk_1', 'company_reports', type_='foreignkey')
    op.drop_constraint('query_results_ibfk_2', 'query_results', type_='foreignkey')
    
    # Recreate foreign keys with CASCADE
    op.create_foreign_key(
        'company_reports_ibfk_1',
        'company_reports',
        'company_info',
        ['company_tax_number'],
        ['tax_number'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'query_results_ibfk_2',
        'query_results',
        'company_info',
        ['company_info_id'],
        ['id'],
        ondelete='CASCADE'
    )

def downgrade():
    # Drop CASCADE foreign keys
    op.drop_constraint('company_reports_ibfk_1', 'company_reports', type_='foreignkey')
    op.drop_constraint('query_results_ibfk_2', 'query_results', type_='foreignkey')
    
    # Recreate original foreign keys without CASCADE
    op.create_foreign_key(
        'company_reports_ibfk_1',
        'company_reports',
        'company_info',
        ['company_tax_number'],
        ['tax_number']
    )
    
    op.create_foreign_key(
        'query_results_ibfk_2',
        'query_results',
        'company_info',
        ['company_info_id'],
        ['id']
    )
