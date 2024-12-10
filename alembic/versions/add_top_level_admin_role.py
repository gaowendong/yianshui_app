"""add top level admin role

Revision ID: add_top_level_admin_role
Revises: f64d50a9274f
Create Date: 2024-01-09 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_top_level_admin_role'
down_revision = 'f64d50a9274f'
branch_labels = None
depends_on = None

def upgrade():
    # MySQL syntax for modifying column
    op.execute("ALTER TABLE users MODIFY COLUMN role VARCHAR(225)")
    
    # Add is_top_level_admin column
    op.add_column('users', sa.Column('is_top_level_admin', sa.Boolean(), nullable=True, server_default='0'))
    
    # Create index for faster role queries
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_is_top_level_admin'), 'users', ['is_top_level_admin'], unique=False)

def downgrade():
    # Remove indexes
    op.drop_index(op.f('ix_users_is_top_level_admin'), table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    
    # Remove is_top_level_admin column
    op.drop_column('users', 'is_top_level_admin')
