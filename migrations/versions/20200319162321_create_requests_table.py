"""Create requests table.

Revision ID: c68c98b6a75e
Revises: 5c821b099cf2
Create Date: 2020-03-19 16:23:21.437029

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pgsql

revision = "c68c98b6a75e"
down_revision = "5c821b099cf2"
branch_labels = None
depends_on = None

SERVER_NOW = sa.func.now()


def upgrade() -> None:
    op.create_table(
        "requests",
        sa.Column("request_id", pgsql.UUID, primary_key=True),
        sa.Column("remote", pgsql.VARCHAR(64), nullable=True),
        sa.Column("method", pgsql.VARCHAR(7), nullable=False),
        sa.Column("path", pgsql.VARCHAR(50), nullable=False),
        sa.Column("body", pgsql.JSONB, nullable=True),
        sa.Column("created_at", pgsql.TIMESTAMP, server_default=SERVER_NOW),
        sa.PrimaryKeyConstraint("request_id"),
    )


def downgrade() -> None:
    op.drop_table("requests")
