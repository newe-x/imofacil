import calendar as calendar_module
import hashlib
import os
from datetime import date, datetime, timedelta, timezone
from functools import wraps

from docx import Document
from flask import Flask, abort, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from models import Assinatura, Contrato, Imovel, LoginAttempt, Locador, db

app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-troque-em-producao")
app.config["TEMPLATES_AUTO_RELOAD"] = True
os.makedirs(app.instance_path, exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(app.instance_path, 'app.db')}"
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "index"

CONTRATOS_DIR = "contratos"
CONTRATOS_GERADOS_DIR = f"{CONTRATOS_DIR}/gerados"
TEMPLATE_PATH = f"{CONTRATOS_DIR}/Contrato_de_Locacao_Residencial.docx"

# Mapeia o nome do campo usado internamente para o placeholder real dentro
# do template .docx (alguns usam acentos, outros não). Campos de foro/data
# de assinatura ({{cidade_locador}}/{{uf_locador}} como comarca,
# {{dia_assinatura}}/{{mes}}/{{ano}}) ficam fora por ora.
FIELD_MAP = {
    # Locatário
    "nome_locatario": "nome_locatario",
    "rg_locatario": "rg_locatario",
    "cpf_locatario": "cpf_locatario",
    "email_locatario": "email_locatario",
    "telefone_locatario": "telefone_locatario",
    "endereco_locatario": "endereço_locatario",
    "nacionalidade_locatario": "nacionalidade_locatario",
    "estado_locatario": "estado_locatario",
    "profissao_locatario": "profissão_locatario",
    # Locador
    "nome_locador": "nome_locador",
    "rg_locador": "rg_locador",
    "cpf_locador": "cpf_locador",
    "email_locador": "email_locador",
    "telefone_locador": "telefone_locador",
    "endereco_locador": "endereço_locador",
    "nacionalidade_locador": "nacionalidade_locador",
    "estado_locador": "estado_locador",
    "profissao_locador": "profissão_locador",
    # Imóvel
    "endereco_imovel": "endereco_imovel",
    "bairro_imovel": "bairro_imovel",
    "cidade_imovel": "cidade_imovel",
    "estado_imovel": "estado_imovel",
    "cep_imovel": "cep_imovel",
    # Termos do contrato
    "duracao_contrato": "duracao_contrato",
    "data_inicio": "data_inicio",
    "data_termino": "data_termino",
    "valor": "valor",
    "forma_pagamento": "forma_pagamento",
}

LOCATARIO_FIELDS = [
    "nome_locatario",
    "rg_locatario",
    "cpf_locatario",
    "email_locatario",
    "telefone_locatario",
    "endereco_locatario",
    "nacionalidade_locatario",
    "estado_locatario",
    "profissao_locatario",
]

PERFIL_FIELDS = [
    "nome",
    "rg",
    "cpf",
    "email",
    "telefone",
    "endereco",
    "nacionalidade",
    "estado_civil",
    "profissao",
]

# Proteção contra força bruta no login: bloqueia por usuário (protege a conta)
# e por IP (protege o servidor de tentar muitos usuários de uma vez).
LOGIN_MAX_TENTATIVAS_USUARIO = 5
LOGIN_MAX_TENTATIVAS_IP = 10
LOGIN_JANELA_BLOQUEIO = timedelta(minutes=15)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Locador, int(user_id))


def locador_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "locador":
            abort(403)
        if not current_user.ativo:
            logout_user()
            abort(403)
        if not current_user.perfil_completo and request.endpoint != "perfil":
            return redirect(url_for("perfil"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def registrar_tentativa_login(usuario, ip, sucesso):
    db.session.add(LoginAttempt(username=usuario, ip=ip, sucesso=sucesso))
    db.session.commit()


def login_bloqueado(usuario, ip):
    limite = datetime.now(timezone.utc).replace(tzinfo=None) - LOGIN_JANELA_BLOQUEIO
    falhas_usuario = LoginAttempt.query.filter(
        LoginAttempt.username == usuario,
        LoginAttempt.sucesso.is_(False),
        LoginAttempt.created_at >= limite,
    ).count()
    falhas_ip = LoginAttempt.query.filter(
        LoginAttempt.ip == ip,
        LoginAttempt.sucesso.is_(False),
        LoginAttempt.created_at >= limite,
    ).count()
    return falhas_usuario >= LOGIN_MAX_TENTATIVAS_USUARIO or falhas_ip >= LOGIN_MAX_TENTATIVAS_IP


def seed_usuarios():
    if Locador.query.first() is None:
        administrador = Locador(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            role="admin",
        )
        locador_teste = Locador(
            username="locador",
            password_hash=generate_password_hash("locador123"),
            role="locador",
        )
        db.session.add_all([administrador, locador_teste])
        db.session.commit()


@app.route("/")
def index():
    if current_user.is_authenticated:
        destino = "admin_locadores" if current_user.role == "admin" else "dashboard"
        return redirect(url_for(destino))
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    usuario = request.form.get("usuario", "").strip()
    senha = request.form.get("senha", "")
    ip = request.remote_addr or "desconhecido"

    if login_bloqueado(usuario, ip):
        return jsonify({"error": "Muitas tentativas de login. Aguarde alguns minutos e tente novamente."}), 429

    user = Locador.query.filter_by(username=usuario).first()
    if not user or not check_password_hash(user.password_hash, senha):
        registrar_tentativa_login(usuario, ip, False)
        return jsonify({"error": "Usuário ou senha inválidos."}), 401
    if not user.ativo:
        registrar_tentativa_login(usuario, ip, False)
        return jsonify({"error": "Sua conta está desativada. Fale com o administrador."}), 403

    registrar_tentativa_login(usuario, ip, True)
    login_user(user)
    destino = "admin_locadores" if user.role == "admin" else "dashboard"
    return jsonify({"result": "Login bem-sucedido!", "redirect": url_for(destino)})


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"result": "Logout realizado com sucesso!"})


@app.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    if request.method == "GET":
        return render_template("perfil.html", primeiro_acesso=not current_user.perfil_completo)

    dados = {campo: request.form.get(campo, "").strip() for campo in PERFIL_FIELDS}
    missing = [campo for campo, valor in dados.items() if not valor]
    if missing:
        return render_template(
            "perfil.html",
            primeiro_acesso=not current_user.perfil_completo,
            dados=dados,
            error="Preencha todos os campos.",
        ), 400

    nova_senha = request.form.get("nova_senha", "")
    if nova_senha and len(nova_senha) < 6:
        return render_template(
            "perfil.html",
            primeiro_acesso=not current_user.perfil_completo,
            dados=dados,
            error="A nova senha precisa ter pelo menos 6 caracteres.",
        ), 400

    for campo, valor in dados.items():
        setattr(current_user, campo, valor)
    if nova_senha:
        current_user.password_hash = generate_password_hash(nova_senha)
    current_user.perfil_completo = True
    db.session.commit()

    destino = "admin_locadores" if current_user.role == "admin" else "dashboard"
    return redirect(url_for(destino))


@app.route("/dashboard")
@locador_required
def dashboard():
    hoje = date.today()
    em_30_dias = hoje + timedelta(days=30)

    total_imoveis = Imovel.query.filter_by(locador_id=current_user.id).count()

    contratos_do_locador = Contrato.query.join(Imovel).filter(Imovel.locador_id == current_user.id)

    alocacoes_realizadas = contratos_do_locador.filter(Contrato.status.in_(["preenchido", "assinado"])).count()
    alocacoes_ativas = contratos_do_locador.filter(
        Contrato.status.in_(["preenchido", "assinado"]),
        Contrato.data_inicio <= hoje,
        Contrato.data_termino >= hoje,
    ).count()
    proximos_30_dias = contratos_do_locador.filter(
        Contrato.data_inicio > hoje,
        Contrato.data_inicio <= em_30_dias,
    ).count()

    return render_template(
        "dashboard.html",
        total_imoveis=total_imoveis,
        alocacoes_realizadas=alocacoes_realizadas,
        alocacoes_ativas=alocacoes_ativas,
        proximos_30_dias=proximos_30_dias,
    )


@app.route("/imoveis")
@locador_required
def imoveis():
    lista = Imovel.query.filter_by(locador_id=current_user.id).order_by(Imovel.created_at.desc()).all()
    return render_template("imoveis_lista.html", imoveis=lista, erro=request.args.get("erro"))


@app.route("/imoveis/novo", methods=["GET", "POST"])
@locador_required
def novo_imovel():
    if request.method == "GET":
        return render_template("imovel_form.html")

    campos = ["nome", "endereco", "bairro", "cidade", "estado", "cep"]
    dados = {campo: request.form.get(campo, "").strip() for campo in campos}

    missing = [campo for campo, valor in dados.items() if not valor]
    if missing:
        return render_template("imovel_form.html", error="Preencha todos os campos.", dados=dados), 400

    imovel = Imovel(locador_id=current_user.id, **dados)
    db.session.add(imovel)
    db.session.commit()
    return redirect(url_for("imoveis"))


@app.route("/imoveis/<int:imovel_id>/editar", methods=["GET", "POST"])
@locador_required
def editar_imovel(imovel_id):
    imovel = Imovel.query.filter_by(id=imovel_id, locador_id=current_user.id).first()
    if not imovel:
        abort(404)

    if request.method == "GET":
        return render_template("imovel_form.html", imovel=imovel)

    campos = ["nome", "endereco", "bairro", "cidade", "estado", "cep"]
    dados = {campo: request.form.get(campo, "").strip() for campo in campos}

    missing = [campo for campo, valor in dados.items() if not valor]
    if missing:
        return render_template(
            "imovel_form.html", imovel=imovel, dados=dados, error="Preencha todos os campos."
        ), 400

    for campo, valor in dados.items():
        setattr(imovel, campo, valor)
    db.session.commit()
    return redirect(url_for("imoveis"))


@app.route("/imoveis/<int:imovel_id>/excluir", methods=["POST"])
@locador_required
def excluir_imovel(imovel_id):
    imovel = Imovel.query.filter_by(id=imovel_id, locador_id=current_user.id).first()
    if not imovel:
        abort(404)

    if imovel.contratos:
        return redirect(url_for("imoveis", erro="Não é possível excluir um imóvel com contratos gerados."))

    db.session.delete(imovel)
    db.session.commit()
    return redirect(url_for("imoveis"))


@app.route("/contratos")
@locador_required
def contratos():
    lista = (
        Contrato.query.join(Imovel)
        .filter(Imovel.locador_id == current_user.id)
        .order_by(Contrato.created_at.desc())
        .all()
    )
    return render_template("contratos_lista.html", contratos=lista)


NOMES_MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


@app.route("/calendario")
@locador_required
def calendario():
    hoje = date.today()
    ano = request.args.get("ano", type=int) or hoje.year
    mes = request.args.get("mes", type=int) or hoje.month
    if mes < 1 or mes > 12:
        mes = hoje.month

    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = date(ano, mes, calendar_module.monthrange(ano, mes)[1])

    contratos_assinados = (
        Contrato.query.join(Imovel)
        .filter(
            Imovel.locador_id == current_user.id,
            Contrato.status == "assinado",
            Contrato.data_inicio <= ultimo_dia,
            Contrato.data_termino >= primeiro_dia,
        )
        .all()
    )

    ocupacoes = {}
    for contrato in contratos_assinados:
        dia = max(contrato.data_inicio, primeiro_dia)
        fim = min(contrato.data_termino, ultimo_dia)
        while dia <= fim:
            ocupacoes.setdefault(dia.day, []).append(
                {"imovel": contrato.imovel.nome, "locatario": contrato.nome_locatario}
            )
            dia += timedelta(days=1)

    semanas = calendar_module.Calendar(firstweekday=6).monthdayscalendar(ano, mes)

    mes_anterior, ano_mes_anterior = (12, ano - 1) if mes == 1 else (mes - 1, ano)
    mes_seguinte, ano_mes_seguinte = (1, ano + 1) if mes == 12 else (mes + 1, ano)

    return render_template(
        "calendario.html",
        semanas=semanas,
        ocupacoes=ocupacoes,
        mes=mes,
        ano=ano,
        nome_mes=NOMES_MESES[mes - 1],
        mes_anterior=mes_anterior,
        ano_mes_anterior=ano_mes_anterior,
        mes_seguinte=mes_seguinte,
        ano_mes_seguinte=ano_mes_seguinte,
        hoje=hoje,
    )


@app.route("/contratos/novo", methods=["GET", "POST"])
@locador_required
def novo_contrato():
    imoveis_do_locador = Imovel.query.filter_by(locador_id=current_user.id).order_by(Imovel.nome).all()

    if request.method == "GET":
        return render_template("contrato_novo.html", imoveis=imoveis_do_locador)

    imovel_id = request.form.get("imovel_id", "")
    imovel = next((i for i in imoveis_do_locador if str(i.id) == imovel_id), None)

    campos = ["duracao_contrato", "data_inicio", "data_termino", "valor", "forma_pagamento"]
    dados = {campo: request.form.get(campo, "").strip() for campo in campos}
    missing = [campo for campo, valor in dados.items() if not valor]

    if not imovel or missing:
        return render_template(
            "contrato_novo.html",
            imoveis=imoveis_do_locador,
            error="Selecione um imóvel e preencha todos os termos do contrato.",
        ), 400

    try:
        data_inicio = date.fromisoformat(dados["data_inicio"])
        data_termino = date.fromisoformat(dados["data_termino"])
    except ValueError:
        return render_template(
            "contrato_novo.html", imoveis=imoveis_do_locador, error="Datas inválidas."
        ), 400

    if (data_termino - data_inicio).days <= 1:
        return render_template(
            "contrato_novo.html",
            imoveis=imoveis_do_locador,
            error="A duração do contrato precisa ser maior que 1 dia.",
        ), 400

    contrato = Contrato(
        imovel_id=imovel.id,
        duracao_contrato=dados["duracao_contrato"],
        data_inicio=data_inicio,
        data_termino=data_termino,
        valor=dados["valor"],
        forma_pagamento=dados["forma_pagamento"],
    )
    db.session.add(contrato)
    db.session.commit()

    link = url_for("contrato_publico", token=contrato.token, _external=True)
    return render_template("contrato_novo.html", imoveis=imoveis_do_locador, link=link)


@app.route("/contratos/<int:contrato_id>/cancelar", methods=["POST"])
@locador_required
def cancelar_contrato(contrato_id):
    contrato = (
        Contrato.query.join(Imovel)
        .filter(Contrato.id == contrato_id, Imovel.locador_id == current_user.id)
        .first()
    )
    if not contrato:
        abort(404)

    if contrato.status == "pendente":
        contrato.status = "cancelado"
        db.session.commit()

    return redirect(url_for("contratos"))


@app.route("/contratos/<int:contrato_id>/reenviar", methods=["POST"])
@locador_required
def reenviar_contrato(contrato_id):
    contrato = (
        Contrato.query.join(Imovel)
        .filter(Contrato.id == contrato_id, Imovel.locador_id == current_user.id)
        .first()
    )
    if not contrato:
        abort(404)

    if contrato.status == "pendente":
        contrato.token_expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
        db.session.commit()

    return redirect(url_for("contratos"))


@app.route("/contratos/<int:contrato_id>/assinar", methods=["GET", "POST"])
@locador_required
def assinar_contrato(contrato_id):
    contrato = (
        Contrato.query.join(Imovel)
        .filter(Contrato.id == contrato_id, Imovel.locador_id == current_user.id)
        .first()
    )
    if not contrato:
        abort(404)

    ja_assinado_pelo_locador = any(a.papel == "locador" for a in contrato.assinaturas)
    if contrato.status != "preenchido" or ja_assinado_pelo_locador:
        return redirect(url_for("contratos"))

    if request.method == "GET":
        return render_template("contrato_assinar.html", contrato=contrato)

    nome = request.form.get("nome", "").strip()
    if not nome:
        return render_template(
            "contrato_assinar.html", contrato=contrato, error="Digite seu nome completo para assinar."
        ), 400

    db.session.add(
        Assinatura(
            contrato_id=contrato.id,
            papel="locador",
            nome=nome,
            ip=request.remote_addr or "desconhecido",
            user_agent=request.headers.get("User-Agent", "")[:255],
            hash_documento=hash_arquivo(f"{CONTRATOS_GERADOS_DIR}/{contrato.token}.docx"),
        )
    )
    contrato.status = "assinado"
    db.session.commit()

    anexar_bloco_assinaturas(contrato)

    return redirect(url_for("contratos"))


@app.route("/contrato/<token>")
def contrato_publico(token):
    contrato = Contrato.query.filter_by(token=token).first()
    if not contrato:
        abort(404)

    if contrato.status == "assinado":
        estado = "assinado"
    elif contrato.status == "preenchido":
        estado = "preenchido"
    elif contrato.status == "cancelado":
        estado = "cancelado"
    elif contrato.link_expirado:
        estado = "expirado"
    else:
        estado = "valido"

    return render_template("cliente.html", token=token, estado=estado)


@app.route("/contrato/<token>/enviar", methods=["POST"])
def enviar_contrato(token):
    contrato = Contrato.query.filter_by(token=token).first()
    if not contrato:
        abort(404)
    if contrato.status == "assinado":
        return jsonify({"error": "Este contrato já foi assinado e não pode mais ser alterado."}), 400
    if contrato.status == "preenchido":
        return jsonify({"error": "Este link já foi utilizado."}), 400
    if contrato.status == "cancelado":
        return jsonify({"error": "Este contrato foi cancelado pelo locador."}), 400
    if contrato.link_expirado:
        return jsonify({"error": "Este link expirou. Peça ao locador para reenviar um novo link."}), 400

    dados_locatario = {campo: request.form.get(campo, "").strip() for campo in LOCATARIO_FIELDS}
    missing = [campo for campo, valor in dados_locatario.items() if not valor]
    if missing:
        return jsonify({"error": f"Campos obrigatórios não preenchidos: {', '.join(missing)}"}), 400

    try:
        gerarContratos(contrato, dados_locatario)
    except FileNotFoundError:
        return jsonify({"error": "Modelo de contrato não encontrado no servidor."}), 500
    except OSError:
        return jsonify({"error": "Não foi possível salvar o contrato gerado."}), 500

    for campo, valor in dados_locatario.items():
        setattr(contrato, campo, valor)
    contrato.status = "preenchido"
    contrato.filled_at = datetime.now(timezone.utc)

    # O checkbox "Aceito os termos e condições" (obrigatório no form) já é o
    # consentimento do locatário — registramos a assinatura dele agora, com
    # o hash do documento que ele acabou de ver/preencher.
    db.session.add(
        Assinatura(
            contrato_id=contrato.id,
            papel="locatario",
            nome=dados_locatario["nome_locatario"],
            documento=dados_locatario["cpf_locatario"],
            ip=request.remote_addr or "desconhecido",
            user_agent=request.headers.get("User-Agent", "")[:255],
            hash_documento=hash_arquivo(f"{CONTRATOS_GERADOS_DIR}/{contrato.token}.docx"),
        )
    )
    db.session.commit()

    return jsonify({"result": "Contrato gerado com sucesso!"})


@app.route("/contrato/<token>/download")
def download_contrato(token):
    contrato = Contrato.query.filter_by(token=token).first()
    if not contrato or contrato.status not in ("preenchido", "assinado"):
        abort(404)
    return send_from_directory(CONTRATOS_GERADOS_DIR, f"{token}.docx", as_attachment=True)


@app.route("/admin")
@admin_required
def admin_locadores():
    locadores = Locador.query.filter_by(role="locador").order_by(Locador.username).all()
    return render_template("admin_locadores.html", locadores=locadores)


@app.route("/admin/locadores/novo", methods=["GET", "POST"])
@admin_required
def admin_novo_locador():
    if request.method == "GET":
        return render_template("admin_locador_form.html")

    usuario = request.form.get("usuario", "").strip()
    senha = request.form.get("senha", "")

    if not usuario or not senha:
        return render_template(
            "admin_locador_form.html", error="Preencha usuário e senha.", usuario=usuario
        ), 400

    if Locador.query.filter_by(username=usuario).first():
        return render_template(
            "admin_locador_form.html", error="Já existe um usuário com esse nome.", usuario=usuario
        ), 400

    locador = Locador(username=usuario, password_hash=generate_password_hash(senha), role="locador")
    db.session.add(locador)
    db.session.commit()
    return redirect(url_for("admin_locadores"))


@app.route("/admin/locadores/<int:locador_id>/alternar-acesso", methods=["POST"])
@admin_required
def admin_alternar_acesso(locador_id):
    locador = Locador.query.filter_by(id=locador_id, role="locador").first()
    if not locador:
        abort(404)

    locador.ativo = not locador.ativo
    db.session.commit()
    return redirect(url_for("admin_locadores"))


@app.route("/admin/tentativas")
@admin_required
def admin_tentativas():
    tentativas = (
        LoginAttempt.query.filter_by(sucesso=False).order_by(LoginAttempt.created_at.desc()).limit(50).all()
    )
    return render_template("admin_tentativas.html", tentativas=tentativas)


def hash_arquivo(caminho):
    with open(caminho, "rb") as arquivo:
        return hashlib.sha256(arquivo.read()).hexdigest()


def anexar_bloco_assinaturas(contrato):
    caminho = f"{CONTRATOS_GERADOS_DIR}/{contrato.token}.docx"
    doc = Document(caminho)
    doc.add_paragraph("")
    doc.add_paragraph("Assinaturas eletrônicas")
    for assinatura in sorted(contrato.assinaturas, key=lambda a: a.assinado_em):
        papel = "Locatário" if assinatura.papel == "locatario" else "Locador"
        linha = f"{papel}: {assinatura.nome}"
        if assinatura.documento:
            linha += f" (doc. {assinatura.documento})"
        linha += f" — assinado em {assinatura.assinado_em.strftime('%d/%m/%Y %H:%M')} pelo IP {assinatura.ip}"
        doc.add_paragraph(linha)
    doc.save(caminho)


def gerarContratos(contrato, dados_locatario):
    imovel = contrato.imovel
    locador = imovel.locador

    dados = dict(dados_locatario)
    dados["nome_locador"] = locador.nome
    dados["rg_locador"] = locador.rg
    dados["cpf_locador"] = locador.cpf
    dados["email_locador"] = locador.email
    dados["telefone_locador"] = locador.telefone
    dados["endereco_locador"] = locador.endereco
    dados["nacionalidade_locador"] = locador.nacionalidade
    dados["estado_locador"] = locador.estado_civil
    dados["profissao_locador"] = locador.profissao
    dados["endereco_imovel"] = imovel.endereco
    dados["bairro_imovel"] = imovel.bairro
    dados["cidade_imovel"] = imovel.cidade
    dados["estado_imovel"] = imovel.estado
    dados["cep_imovel"] = imovel.cep
    dados["duracao_contrato"] = contrato.duracao_contrato
    dados["data_inicio"] = contrato.data_inicio.strftime("%d/%m/%Y")
    dados["data_termino"] = contrato.data_termino.strftime("%d/%m/%Y")
    dados["valor"] = contrato.valor
    dados["forma_pagamento"] = contrato.forma_pagamento

    doc = Document(TEMPLATE_PATH)
    for paragraph in doc.paragraphs:
        for field, value in dados.items():
            placeholder = "{{" + FIELD_MAP[field] + "}}"
            if placeholder in paragraph.text:
                paragraph.text = paragraph.text.replace(placeholder, value or "")

    os.makedirs(CONTRATOS_GERADOS_DIR, exist_ok=True)
    doc.save(f"{CONTRATOS_GERADOS_DIR}/{contrato.token}.docx")


with app.app_context():
    db.create_all()
    seed_usuarios()


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
