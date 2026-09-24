import re
from decimal import Decimal, InvalidOperation

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def so_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def cpf_valido(cpf):
    numeros = so_digitos(cpf)
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(numeros[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(numeros[tamanho]):
            return False
    return True


def rg_valido(rg):
    # Cada estado tem seu formato de RG; exigimos só o mínimo comum a todos:
    # de 5 a 14 caracteres entre dígitos e o "X" do dígito verificador.
    return 5 <= len(re.sub(r"[^0-9Xx]", "", rg or "")) <= 14


def telefone_valido(telefone):
    # DDD + número: 10 dígitos (fixo) ou 11 (celular).
    return len(so_digitos(telefone)) in (10, 11)


def email_valido(email):
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or "") is not None


def cep_valido(cep):
    return len(so_digitos(cep)) == 8


def uf_valida(uf):
    return (uf or "").strip().upper() in UFS


def parse_valor(texto):
    # Aceita "1800", "1.800", "1800,50", "R$ 1.800,50" e "1800.50".
    # Retorna Decimal ou None se não for um valor positivo.
    limpo = re.sub(r"[^\d,.]", "", texto or "")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif limpo.count(".") > 1 or re.fullmatch(r"\d{1,3}(\.\d{3})+", limpo):
        # "1.800" ou "1.800.000": ponto como separador de milhar
        limpo = limpo.replace(".", "")
    try:
        valor = Decimal(limpo).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return valor if valor > 0 else None


VALIDADORES = {
    "cpf": (cpf_valido, "CPF inválido."),
    "rg": (rg_valido, "RG inválido."),
    "telefone": (telefone_valido, "Telefone inválido — informe DDD + número."),
    "email": (email_valido, "Email inválido."),
    "cep": (cep_valido, "CEP inválido — informe os 8 dígitos."),
    "uf": (uf_valida, "UF inválida — use a sigla do estado (ex: SP)."),
}


def validar(campos):
    # campos: {"cpf": "123...", "email": "..."} -> primeira mensagem de erro ou None
    for tipo, valor in campos.items():
        verifica, mensagem = VALIDADORES[tipo]
        if not verifica(valor):
            return mensagem
    return None
