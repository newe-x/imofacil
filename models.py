import secrets
from datetime import datetime, timedelta, timezone

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Locador(UserMixin, db.Model):
    __tablename__ = "locadores"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # "locador" (cadastra imóveis e contratos) ou "admin" (Administrador,
    # cuida do acesso dos locadores).
    role = db.Column(db.String(20), nullable=False, default="locador")
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    # Dados pessoais, usados no parágrafo "LOCADOR:" do contrato gerado.
    # Só são obrigatórios pra quem tem role "locador" (ver perfil_completo).
    nome = db.Column(db.String(200))
    rg = db.Column(db.String(20))
    cpf = db.Column(db.String(20))
    email = db.Column(db.String(200))
    telefone = db.Column(db.String(30))
    endereco = db.Column(db.String(255))
    nacionalidade = db.Column(db.String(80))
    estado_civil = db.Column(db.String(50))
    profissao = db.Column(db.String(120))
    perfil_completo = db.Column(db.Boolean, nullable=False, default=False)

    imoveis = db.relationship("Imovel", backref="locador", lazy=True)


class Imovel(db.Model):
    __tablename__ = "imoveis"

    id = db.Column(db.Integer, primary_key=True)
    locador_id = db.Column(db.Integer, db.ForeignKey("locadores.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    endereco = db.Column(db.String(255), nullable=False)
    bairro = db.Column(db.String(120), nullable=False)
    cidade = db.Column(db.String(120), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    cep = db.Column(db.String(9), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    contratos = db.relationship("Contrato", backref="imovel", lazy=True)


class Contrato(db.Model):
    __tablename__ = "contratos"

    id = db.Column(db.Integer, primary_key=True)
    imovel_id = db.Column(db.Integer, db.ForeignKey("imoveis.id"), nullable=False)
    token = db.Column(db.String(32), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(12))
    # "pendente" | "preenchido" | "cancelado"
    status = db.Column(db.String(20), nullable=False, default="pendente")
    # SQLite guarda datetime "naive" (sem tzinfo), então geramos/comparamos
    # sempre em UTC sem tzinfo pra evitar erro de comparação naive x aware.
    token_expires_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24),
    )

    # Termos definidos pelo locador ao gerar o contrato.
    duracao_contrato = db.Column(db.String(50), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_termino = db.Column(db.Date, nullable=False)
    valor = db.Column(db.String(50), nullable=False)
    forma_pagamento = db.Column(db.String(120), nullable=False)

    # Dados do locatário, preenchidos via o link público.
    nome_locatario = db.Column(db.String(200))
    rg_locatario = db.Column(db.String(20))
    cpf_locatario = db.Column(db.String(20))
    email_locatario = db.Column(db.String(200))
    telefone_locatario = db.Column(db.String(30))
    endereco_locatario = db.Column(db.String(255))
    nacionalidade_locatario = db.Column(db.String(80))
    estado_locatario = db.Column(db.String(50))
    profissao_locatario = db.Column(db.String(120))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    filled_at = db.Column(db.DateTime)

    @property
    def valor_formatado(self):
        # O locador pode digitar "1800" ou "R$ 1.800,00"; o contrato sempre
        # mostra com "R$" uma única vez.
        valor = self.valor.strip()
        return valor if valor.upper().startswith("R$") else f"R$ {valor}"

    @property
    def link_expirado(self):
        agora = datetime.now(timezone.utc).replace(tzinfo=None)
        return self.status == "pendente" and self.token_expires_at < agora


class LoginAttempt(db.Model):
    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    ip = db.Column(db.String(45), nullable=False)
    sucesso = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class Assinatura(db.Model):
    __tablename__ = "assinaturas"

    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("contratos.id"), nullable=False)
    # "locatario" ou "locador".
    papel = db.Column(db.String(20), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    documento = db.Column(db.String(20))
    ip = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(255))
    # sha256 do .docx gerado no momento da assinatura, prova de que o
    # signatário concordou com aquele conteúdo específico.
    hash_documento = db.Column(db.String(64), nullable=False)
    assinado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    contrato = db.relationship("Contrato", backref="assinaturas")
