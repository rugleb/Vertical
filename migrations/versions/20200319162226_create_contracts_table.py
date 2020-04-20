"""Create contracts table.

Revision ID: 5c821b099cf2
Revises: 9f02be65b5d3
Create Date: 2020-03-19 16:22:26.814311

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, VARCHAR

revision = "5c821b099cf2"
down_revision = "9f02be65b5d3"
branch_labels = None
depends_on = None

SERVER_NOW = sa.func.now()
SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("contract_id", UUID, server_default=SERVER_UUID),
        sa.Column("client_id", UUID, nullable=False),
        sa.Column("token", VARCHAR(64), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=SERVER_NOW),
        sa.Column("expired_at", TIMESTAMP, nullable=True),
        sa.Column("revoked_at", TIMESTAMP, nullable=True),
        sa.PrimaryKeyConstraint(
            "contract_id",
        ),
        sa.ForeignKeyConstraint(
            columns=("client_id", ),
            refcolumns=("clients.client_id", ),
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("contracts")
