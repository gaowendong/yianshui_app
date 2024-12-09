"""update_company_report_user_relationship

Revision ID: f64d50a9274f
Revises: 84816c7fc270
Create Date: 2024-12-09 13:07:48.734155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'f64d50a9274f'
down_revision: Union[str, None] = '84816c7fc270'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Update any null processed_by_user_id values with user_id values
    op.execute('UPDATE company_reports SET processed_by_user_id = user_id WHERE processed_by_user_id IS NULL')
    
    # Drop the old foreign key if it exists
    try:
        op.drop_constraint('company_reports_ibfk_2', 'company_reports', type_='foreignkey')
    except:
        pass

    # Create the new foreign key for processed_by_user_id if it doesn't exist
    try:
        op.create_foreign_key(
            'fk_company_reports_processed_by_user', 
            'company_reports', 'users',
            ['processed_by_user_id'], ['id'],
            ondelete='CASCADE'
        )
    except:
        pass

    # Drop the old user_id column
    op.drop_column('company_reports', 'user_id')
    
    # Drop the channel admin foreign key if it exists
    try:
        op.drop_constraint('channels_ibfk_3', 'channels', type_='foreignkey')
    except:
        pass


def downgrade() -> None:
    # Add old column as nullable
    op.add_column('company_reports', sa.Column('user_id', mysql.INTEGER(), nullable=True))
    
    # Copy data back
    op.execute('UPDATE company_reports SET user_id = processed_by_user_id')
    
    # Make old column non-nullable
    op.alter_column('company_reports', 'user_id',
                    existing_type=mysql.INTEGER(),
                    nullable=False)
    
    # Create old foreign key
    op.create_foreign_key(
        'company_reports_ibfk_2',
        'company_reports', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Recreate channel admin foreign key
    op.create_foreign_key(
        'channels_ibfk_3',
        'channels', 'users',
        ['channel_admin_id'], ['id']
    )
