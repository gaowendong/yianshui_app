"""add_query_results_relationships

Revision ID: 068dbf7ae0c8
Revises: 5be0592cd9e0
Create Date: 2024-11-29 15:03:25.082601

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '068dbf7ae0c8'
down_revision: Union[str, None] = '5be0592cd9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create index and foreign key only, since table already exists
    try:
        op.create_index(op.f('ix_query_results_id'), 'query_results', ['id'], unique=False)
    except Exception:
        pass  # Index might already exist
        
    try:
        op.create_foreign_key(None, 'users', 'users', ['first_level_channel_id'], ['id'])
    except Exception:
        pass  # Foreign key might already exist

    # Modify query_data column to ensure correct length
    try:
        op.alter_column('query_results', 'query_data',
                       existing_type=sa.String(length=255),
                       type_=sa.String(length=1000),
                       existing_nullable=True)
    except Exception:
        pass  # Column might already have correct type


def downgrade() -> None:
    try:
        op.drop_constraint(None, 'users', type_='foreignkey')
    except Exception:
        pass
        
    try:
        op.drop_index(op.f('ix_query_results_id'), table_name='query_results')
    except Exception:
        pass
