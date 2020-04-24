"""Create contract for Yandex Vertical.

Revision ID: c254afd80c93
Revises: be0f06ec00b4
Create Date: 2020-04-24 17:30:45.500575

"""

import secrets

from alembic import op
from sqlalchemy.orm import Session

from vertical.app.auth import Client, Contract

revision = "c254afd80c93"
down_revision = "be0f06ec00b4"
branch_labels = None
depends_on = None


def make_token() -> str:
    return secrets.token_hex()


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    client = Client(name="Yandex Vertical")
    token = make_token()

    contract = Contract(token=token, client=client)
    session.add(contract)
    session.commit()

    session.close()


def downgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    client = session.query(Client) \
        .filter(Client.name == "Yandex Vertical") \
        .first()

    session.query(Contract).filter(Contract.client == client).delete()
    session.delete(client)

    session.commit()
    session.close()
