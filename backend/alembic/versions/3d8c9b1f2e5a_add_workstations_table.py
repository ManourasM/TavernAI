"""add workstations table

Revision ID: 3d8c9b1f2e5a
Revises: 7610f4bb93c2
Create Date: 2026-02-24 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d8c9b1f2e5a'
down_revision = '7610f4bb93c2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create workstations table
    op.create_table(
        'workstations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_workstations_id', 'workstations', ['id'], unique=False)
    op.create_index('ix_workstations_name', 'workstations', ['name'], unique=False)
    op.create_index('ix_workstations_slug', 'workstations', ['slug'], unique=True)
    op.create_index('ix_workstations_active', 'workstations', ['active'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_workstations_active', table_name='workstations')
    op.drop_index('ix_workstations_slug', table_name='workstations')
    op.drop_index('ix_workstations_name', table_name='workstations')
    op.drop_index('ix_workstations_id', table_name='workstations')
    
    # Drop table
    op.drop_table('workstations')
