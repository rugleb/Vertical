"""Create contract for admin.

Revision ID: be0f06ec00b4
Revises: 7b7f7733db71
Create Date: 2020-04-20 18:12:50.053551

"""

import secrets

from alembic import op
from sqlalchemy.orm import Session

from vertical.app.auth import Client, Contract

revision = "be0f06ec00b4"
down_revision = "7b7f7733db71"
branch_labels = None
depends_on = None


def make_token() -> str:
    return secrets.token_hex()


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    admin = Client(name="admin")
    token = make_token()

    contract = Contract(token=token, client=admin)
    session.add(contract)
    session.commit()

    session.close()


def downgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    admin = session.query(Client).filter(Client.name == "admin").first()

    session.query(Contract).filter(Contract.client == admin).delete()
    session.delete(admin)

    session.commit()
    session.close()
