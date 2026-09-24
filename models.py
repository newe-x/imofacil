import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def agora_utc():
    # SQLite guarda datetime "naive" (sem tzinfo): gravamos sempre em UTC sem
    # tzinfo e convertemos para o horário de Brasília só na exibição.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def formatar_moeda(valor):
    # 1234.5 -> "R$ 1.234,50"
    texto = f"{Decimal(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


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
    # Senha definida pelo admin (conta nova ou redefinição): o usuário é
    # obrigado a trocar no próximo login.
    senha_temporaria = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

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
    created_at = db.Column(db.DateTime, default=agora_utc)

    contratos = db.relationship("Contrato", backref="imovel", lazy=True)


class Contrato(db.Model):
    __tablename__ = "contratos"

    id = db.Column(db.Integer, primary_key=True)
    imovel_id = db.Column(db.Integer, db.ForeignKey("imoveis.id"), nullable=False)
    token = db.Column(db.String(32), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(12))
    # "pendente" | "preenchido" | "assinado" | "cancelado"
    status = db.Column(db.String(20), nullable=False, default="pendente")
    token_expires_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: agora_utc() + timedelta(hours=24),
    )

    # Termos definidos pelo locador ao gerar o contrato.
    duracao_contrato = db.Column(db.String(50), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_termino = db.Column(db.Date, nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
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

    created_at = db.Column(db.DateTime, default=agora_utc)
    filled_at = db.Column(db.DateTime)
    # sha256 do .docx final (com o bloco de assinaturas), gravado quando o
    # locador assina — base da verificação de integridade do arquivo.
    hash_final = db.Column(db.String(64))

    @property
    def valor_formatado(self):
        return formatar_moeda(self.valor)

    @property
    def link_expirado(self):
        return self.status == "pendente" and self.token_expires_at < agora_utc()

    @property
    def ultima_assinatura_em(self):
        return max((a.assinado_em for a in self.assinaturas), default=None)


class LoginAttempt(db.Model):
    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    ip = db.Column(db.String(45), nullable=False)
    sucesso = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=agora_utc)


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
    assinado_em = db.Column(db.DateTime, default=agora_utc)

    contrato = db.relationship("Contrato", backref="assinaturas")
