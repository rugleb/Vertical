"""Create identifications table.

Revision ID: 7b7f7733db71
Revises: 5591d429b7e3
Create Date: 2020-03-19 16:28:32.864078

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pgsql

revision = "7b7f7733db71"
down_revision = "5591d429b7e3"
branch_labels = None
depends_on = None

SERVER_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    op.create_table(
        "identifications",
        sa.Column("identification_id", pgsql.UUID, server_default=SERVER_UUID),
        sa.Column("request_id", pgsql.UUID, nullable=False),
        sa.Column("contract_id", pgsql.UUID, nullable=False),
        sa.PrimaryKeyConstraint(
            "identification_id",
        ),
        sa.UniqueConstraint(
            "request_id",
            "contract_id",
        ),
        sa.ForeignKeyConstraint(
            ("request_id", ),
            ("requests.request_id", ),
        ),
        sa.ForeignKeyConstraint(
            ("contract_id", ),
            ("contracts.contract_id", ),
        ),
    )


def downgrade() -> None:
    op.drop_table("identifications")
