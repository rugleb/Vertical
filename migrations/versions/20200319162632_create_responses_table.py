"""Create responses table.

Revision ID: 5591d429b7e3
Revises: c68c98b6a75e
Create Date: 2020-03-19 16:26:32.561625

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pgsql

revision = "5591d429b7e3"
down_revision = "c68c98b6a75e"
branch_labels = None
depends_on = None

SERVER_NOW = sa.func.now()


def upgrade() -> None:
    op.create_table(
        "responses",
        sa.Column("request_id", pgsql.UUID, primary_key=True),
        sa.Column("body", pgsql.JSONB, nullable=True),
        sa.Column("code", pgsql.SMALLINT, nullable=False),
        sa.Column("created_at", pgsql.TIMESTAMP, server_default=SERVER_NOW),
        sa.ForeignKeyConstraint(
            ("request_id", ),
            ("requests.request_id", ),
        ),
    )


def downgrade() -> None:
    op.drop_table("responses")
