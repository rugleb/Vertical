"""Create identifications table.

Revision ID: 7b7f7733db71
Revises: 5591d429b7e3
Create Date: 2020-03-19 16:28:32.864078

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "7b7f7733db71"
down_revision = "5591d429b7e3"
branch_labels = None
depends_on = None

SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "identifications",
        sa.Column("identification_id", UUID, server_default=SERVER_UUID),
        sa.Column("request_id", UUID, nullable=False),
        sa.Column("contract_id", UUID, nullable=False),
        sa.PrimaryKeyConstraint(
            "identification_id",
        ),
        sa.UniqueConstraint(
            "request_id",
            "contract_id",
        ),
        sa.ForeignKeyConstraint(
            columns=("contract_id", ),
            refcolumns=("contracts.contract_id", ),
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    op.drop_table("identifications")
