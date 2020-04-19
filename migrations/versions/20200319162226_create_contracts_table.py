"""Create contracts table.

Revision ID: 5c821b099cf2
Revises: 9f02be65b5d3
Create Date: 2020-03-19 16:22:26.814311

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pgsql

revision = "5c821b099cf2"
down_revision = "9f02be65b5d3"
branch_labels = None
depends_on = None

SERVER_NOW = sa.func.now()
SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("contract_id", pgsql.UUID, server_default=SERVER_UUID),
        sa.Column("client_id", pgsql.UUID, nullable=False),
        sa.Column("token", pgsql.VARCHAR(64), nullable=False),
        sa.Column("created_at", pgsql.TIMESTAMP, server_default=SERVER_NOW),
        sa.Column("expired_at", pgsql.TIMESTAMP, nullable=True),
        sa.Column("revoked_at", pgsql.TIMESTAMP, nullable=True),
        sa.PrimaryKeyConstraint(
            "contract_id",
        ),
        sa.ForeignKeyConstraint(
            ("client_id", ),
            ("clients.client_id", ),
        ),
    )


def downgrade() -> None:
    op.drop_table("contracts")
