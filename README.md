# Imofácil

Plataforma para locadores cadastrarem imóveis, gerarem contratos de locação
por link único e coletarem os dados e a assinatura eletrônica do locatário
— sem o locatário precisar criar conta.

## Papéis

- **Locador** — cadastra imóveis, gera contratos (define os termos:
  duração, datas, valor, forma de pagamento), acompanha o status de cada
  contrato, assina os contratos já preenchidos pelo locatário e visualiza
  a ocupação dos imóveis num calendário.
- **Administrador** — não cadastra imóveis; gerencia o acesso das contas
  de locador (criar, ativar/desativar) e audita tentativas de login
  malsucedidas.
- **Locatário** — não faz login. Recebe um link público exclusivo por
  contrato, preenche seus dados e assina eletronicamente. O link expira em
  24h e pode ser reenviado pelo locador.

## Funcionalidades

- Cadastro, edição e exclusão de imóveis (exclusão bloqueada se o imóvel
  já tiver contratos gerados).
- Geração de contrato por link único (token), com expiração de 24h e opção
  de reenvio.
- Preenchimento dos dados do locatário via link público, com validação de
  duração mínima do contrato (> 1 dia).
- **Leitura antes de assinar**: o link público mostra um resumo em linguagem
  simples e o contrato completo, com os dados do locatário preenchidos
  enquanto ele digita; o aceite só é liberado após rolar o texto até o fim.
- **Assinatura eletrônica em duas etapas**: o locatário assina ao aceitar
  os termos no preenchimento; o locador revisa e assina depois. Cada
  assinatura registra nome, documento, IP, user-agent e o hash SHA-256 do
  `.docx` no momento da assinatura — quando ambas existem, um bloco de
  assinaturas é anexado ao contrato final e o status vira `assinado`.
- Cancelamento de contratos pendentes.
- Geração do contrato final em `.docx` a partir de um template, mesclando
  dados do imóvel, termos do contrato e dados do locatário.
- **Calendário de ocupação**: períodos de contratos assinados aparecem em
  vermelho, com tooltip mostrando imóvel e locatário ao passar o mouse.
- **Painel administrativo**: criação de contas de locador, ativação e
  desativação de acesso (com invalidação imediata da sessão), e log de
  tentativas de login malsucedidas.
- **Segurança de login**: rate limiting (5 tentativas falhas por usuário
  ou 10 por IP em 15 minutos) e auditoria de tentativas malsucedidas.

## Stack

- Python 3.11, Flask, Flask-SQLAlchemy, Flask-Login
- SQLite (arquivo em `instance/app.db`)
- `python-docx` para geração dos contratos
- Gunicorn como servidor WSGI em produção/Docker

## Rodando localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

flask run
```

A aplicação sobe em `http://127.0.0.1:5000`. No primeiro start, o banco é
criado automaticamente em `instance/app.db` e duas contas são semeadas:

| Usuário   | Senha         | Papel   |
|-----------|---------------|---------|
| `admin`   | `admin123`    | admin   |
| `locador` | `locador123`  | locador |

Troque essas senhas (ou crie novas contas de locador via painel
administrativo) antes de qualquer uso real.

## Rodando com Docker

```bash
cp .env.example .env   # defina SECRET_KEY
docker compose up -d --build
```

A aplicação sobe em `http://localhost:5000`, servida por Gunicorn. Os
volumes `./instance` e `./contratos/gerados` são montados no container
para persistir o banco e os contratos gerados entre reinícios.

## Variáveis de ambiente

| Variável     | Descrição                                   | Padrão (dev)                        |
|--------------|----------------------------------------------|--------------------------------------|
| `SECRET_KEY` | Chave de sessão do Flask                     | `dev-secret-key-troque-em-producao` |

## Estrutura do projeto

```
app.py                  # rotas e regras de negócio
models.py                # modelos SQLAlchemy (Locador, Imovel, Contrato, Assinatura, LoginAttempt)
templates/                # views Jinja
static/                   # CSS, JS e imagens
contratos/
  Contrato_de_Locacao_Residencial.docx   # template usado na geração
  gerados/                                # contratos .docx gerados (não versionado)
instance/                 # banco SQLite (não versionado)
```

## Fluxo de um contrato

1. Locador cadastra o imóvel e cria um contrato definindo os termos →
   recebe um link único (`/contrato/<token>`).
2. Locatário abre o link, preenche seus dados pessoais e aceita os termos
   → isso já registra a assinatura eletrônica dele; o `.docx` é gerado e o
   contrato passa a `preenchido`.
3. Locador revisa e assina em `/contratos/<id>/assinar` → o contrato passa
   a `assinado` e o bloco de assinaturas é anexado ao `.docx` final.
4. O período do contrato aparece em vermelho no calendário de ocupação.

Links não usados em 24h expiram (`link_expirado`); o locador pode reenviar
um novo prazo a qualquer momento enquanto o contrato estiver `pendente`.
