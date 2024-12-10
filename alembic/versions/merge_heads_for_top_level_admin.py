"""merge heads for top level admin

Revision ID: merge_heads_for_top_level_admin
Revises: add_top_level_admin_role, f64d50a9274f
Create Date: 2024-01-09 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_for_top_level_admin'
down_revision = ('add_top_level_admin_role', 'f64d50a9274f')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
