"""initial

Revision ID: c738cf2cda76
Revises: 
Create Date: 2026-04-06 21:02:45.595028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


                                        
revision: str = 'c738cf2cda76'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
                                                                 
    op.create_index('ix_recovery_user_date', 'daily_recovery', ['user_id', 'date'], unique=False)
                                  


def downgrade() -> None:
    """Downgrade schema."""
                                                                 
    op.drop_index('ix_recovery_user_date', table_name='daily_recovery')
                                  
