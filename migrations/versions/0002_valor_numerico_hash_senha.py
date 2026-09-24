"""valor numérico, hash final do contrato e senha temporária

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-24 13:00:00

"""
import os
import sys

from alembic import op
import sqlalchemy as sa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from validacao import parse_valor  # noqa: E402


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('locadores', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('senha_temporaria', sa.Boolean(), nullable=False, server_default=sa.false())
        )

    with op.batch_alter_table('contratos', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hash_final', sa.String(length=64), nullable=True))

    # "valor" era texto livre ("1800", "R$ 1.800,00"...): converte cada linha
    # para número antes de trocar o tipo da coluna.
    conexao = op.get_bind()
    for id_, valor in conexao.execute(sa.text("SELECT id, valor FROM contratos")).fetchall():
        numero = parse_valor(str(valor))
        if numero is None:
            raise RuntimeError(f"Contrato {id_}: não foi possível converter o valor {valor!r} para número.")
        conexao.execute(
            sa.text("UPDATE contratos SET valor = :valor WHERE id = :id"), {"valor": str(numero), "id": id_}
        )

    with op.batch_alter_table('contratos', schema=None) as batch_op:
        batch_op.alter_column(
            'valor', existing_type=sa.String(length=50), type_=sa.Numeric(10, 2), existing_nullable=False
        )


def downgrade():
    with op.batch_alter_table('contratos', schema=None) as batch_op:
        batch_op.alter_column(
            'valor', existing_type=sa.Numeric(10, 2), type_=sa.String(length=50), existing_nullable=False
        )
        batch_op.drop_column('hash_final')

    with op.batch_alter_table('locadores', schema=None) as batch_op:
        batch_op.drop_column('senha_temporaria')
