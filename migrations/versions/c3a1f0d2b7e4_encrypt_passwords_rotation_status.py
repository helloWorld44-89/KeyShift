"""encrypt stored Wi-Fi passwords; add rotation status columns

Revision ID: c3a1f0d2b7e4
Revises: bfabed8737bc
Create Date: 2026-10-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

from app.crypto import decrypt, encrypt, is_encrypted


# revision identifiers, used by Alembic.
revision = 'c3a1f0d2b7e4'
down_revision = 'bfabed8737bc'
branch_labels = None
depends_on = None


def _rewrite_passwords(convert):
    """Apply convert() to every stored SSID password with raw SQL (bypassing the column type)."""
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, ssidPW FROM ssids WHERE ssidPW IS NOT NULL AND ssidPW != ''")).fetchall()
    for row_id, value in rows:
        conn.execute(sa.text("UPDATE ssids SET ssidPW = :v WHERE id = :id"),
                     {"v": convert(value), "id": row_id})


def upgrade():
    with op.batch_alter_table('ssids', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pendingPW', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('lastAttempt', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('failCount', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('lastError', sa.Text(), nullable=True))
    op.execute("UPDATE ssids SET failCount = 0")
    _rewrite_passwords(lambda v: v if is_encrypted(v) else encrypt(v))


def downgrade():
    _rewrite_passwords(decrypt)
    with op.batch_alter_table('ssids', schema=None) as batch_op:
        batch_op.drop_column('lastError')
        batch_op.drop_column('failCount')
        batch_op.drop_column('lastAttempt')
        batch_op.drop_column('pendingPW')
