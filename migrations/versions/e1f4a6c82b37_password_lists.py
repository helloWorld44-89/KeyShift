"""password lists: ssid_passwords table and list columns on ssids

Revision ID: e1f4a6c82b37
Revises: d7b2e9a41c05
Create Date: 2026-10-28 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1f4a6c82b37'
down_revision = 'd7b2e9a41c05'
branch_labels = None
depends_on = None

COLUMNS = [
    ('listEnabled', sa.Boolean()),
    ('listMode', sa.Text()),
    ('listIndex', sa.Integer()),
    ('listOnEnd', sa.Text()),
    ('listCurrentId', sa.Integer()),
]


def upgrade():
    inspector = sa.inspect(op.get_bind())
    have = {c['name'] for c in inspector.get_columns('ssids')}
    missing = [(n, t) for n, t in COLUMNS if n not in have]  # skip columns a half-applied run added
    if missing:
        with op.batch_alter_table('ssids', schema=None) as batch_op:
            for name, type_ in missing:
                batch_op.add_column(sa.Column(name, type_, nullable=True))
    op.execute("UPDATE ssids SET listEnabled = 0, listMode = 'sequential', listIndex = 0, "
               "listOnEnd = 'restart' WHERE listEnabled IS NULL")
    if 'ssid_passwords' not in inspector.get_table_names():
        op.create_table('ssid_passwords',
                        sa.Column('id', sa.Integer(), nullable=False),
                        sa.Column('ssid_id', sa.Integer(), nullable=False),
                        sa.Column('password', sa.Text(), nullable=False),
                        sa.Column('position', sa.Integer(), nullable=False),
                        sa.Column('lastUsed', sa.DateTime(), nullable=True),
                        sa.ForeignKeyConstraint(['ssid_id'], ['ssids.id']),
                        sa.PrimaryKeyConstraint('id'))


def downgrade():
    op.drop_table('ssid_passwords')
    with op.batch_alter_table('ssids', schema=None) as batch_op:
        for name, _ in reversed(COLUMNS):
            batch_op.drop_column(name)
