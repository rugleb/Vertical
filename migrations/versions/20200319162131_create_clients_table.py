"""Create clients table.

Revision ID: 9f02be65b5d3
Revises: None
Create Date: 2020-03-19 16:21:31.808712

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pgsql

revision = "9f02be65b5d3"
down_revision = "98529cf9ab14"
branch_labels = None
depends_on = None

SERVER_NOW = sa.func.now()
SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("client_id", pgsql.UUID, server_default=SERVER_UUID),
        sa.Column("name", pgsql.VARCHAR(64), nullable=False),
        sa.Column("created_at", pgsql.TIMESTAMP, server_default=SERVER_NOW),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("clients")
