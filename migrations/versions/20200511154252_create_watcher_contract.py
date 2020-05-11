"""Create watcher contract.

Revision ID: 99574da7cd18
Revises: c254afd80c93
Create Date: 2020-05-11 15:42:52.814598

"""

import secrets

from alembic import op
from sqlalchemy.orm import Session

from vertical.app.auth import Client, Contract

revision = "99574da7cd18"
down_revision = "c254afd80c93"
branch_labels = None
depends_on = None


def make_token() -> str:
    return secrets.token_hex()


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    client = Client(name="Watcher")
    token = make_token()

    contract = Contract(token=token, client=client)
    session.add(contract)
    session.commit()

    session.close()


def downgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    client = session.query(Client) \
        .filter(Client.name == "Watcher") \
        .first()

    session.query(Contract).filter(Contract.client == client).delete()
    session.delete(client)

    session.commit()
    session.close()
