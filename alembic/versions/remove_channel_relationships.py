"""remove channel relationships

Revision ID: remove_channel_rel
Revises: 
Create Date: 2024-01-09 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_channel_rel'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # First check if the column exists before trying to drop it
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('company_info')]
    
    if 'channel_id' in columns:
        # Drop all foreign key constraints on the channel_id column
        op.execute('ALTER TABLE company_info DROP FOREIGN KEY company_info_ibfk_2')
        try:
            op.drop_constraint('company_info_channel_id_fkey', 'company_info', type_='foreignkey')
        except:
            pass  # Constraint might not exist
        
        # Drop the column
        op.drop_column('company_info', 'channel_id')

def downgrade():
    # Add back the channel_id column to company_info table
    op.add_column('company_info', sa.Column('channel_id', sa.Integer(), nullable=True))
    op.create_foreign_key('company_info_channel_id_fkey', 'company_info', 'channels', ['channel_id'], ['id'])
