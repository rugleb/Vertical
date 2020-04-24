"""Create clients table.

Revision ID: 9f02be65b5d3
Revises: None
Create Date: 2020-03-19 16:21:31.808712

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, VARCHAR

revision = "9f02be65b5d3"
down_revision = "98529cf9ab14"
branch_labels = None
depends_on = None

SERVER_NOW = sa.func.now()
SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("client_id", UUID, server_default=SERVER_UUID),
        sa.Column("name", VARCHAR(64), nullable=False),
        sa.Column("created_at", TIMESTAMP, server_default=SERVER_NOW),
        sa.PrimaryKeyConstraint("client_id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("clients")
