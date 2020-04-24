"""Create pgcrypto extension.

Revision ID: 98529cf9ab14
Revises: 6b82dcd34510
Create Date: 2020-03-19 17:11:25.100988

"""

from alembic import op

revision = "98529cf9ab14"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
