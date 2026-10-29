"""add the settings table (password policy)

Revision ID: d7b2e9a41c05
Revises: c3a1f0d2b7e4
Create Date: 2026-10-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7b2e9a41c05'
down_revision = 'c3a1f0d2b7e4'
branch_labels = None
depends_on = None


def upgrade():
    if 'settings' in sa.inspect(op.get_bind()).get_table_names():
        return  # a half-applied earlier run; nothing to do
    op.create_table('settings',
                    sa.Column('key', sa.Text(), nullable=False),
                    sa.Column('value', sa.Text(), nullable=True),
                    sa.PrimaryKeyConstraint('key'))


def downgrade():
    op.drop_table('settings')
