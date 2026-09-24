# Imofácil

Plataforma para locadores cadastrarem imóveis, gerarem contratos de locação
por link único e coletarem os dados e a assinatura eletrônica do locatário
— sem o locatário precisar criar conta.

## Papéis

- **Locador** — no primeiro acesso completa o perfil (dados pessoais
  usados na qualificação do LOCADOR no contrato); depois cadastra imóveis,
  gera contratos (define os termos:
  duração, datas, valor, forma de pagamento), acompanha o status de cada
  contrato, assina os contratos já preenchidos pelo locatário e visualiza
  a ocupação dos imóveis num calendário.
- **Administrador** — não cadastra imóveis; gerencia o acesso das contas
  de locador (criar, ativar/desativar, redefinir senha) e audita tentativas
  de login malsucedidas. O perfil dele serve só para trocar a senha.
- **Locatário** — não faz login. Recebe um link público exclusivo por
  contrato, preenche seus dados e assina eletronicamente. O link expira em
  24h e pode ser reenviado pelo locador.

## Funcionalidades

- **Perfil do locador** (`/perfil`): nome, RG, CPF, contato, endereço,
  nacionalidade, estado civil e profissão, com CPF/RG/telefone formatados
  automaticamente e validados no servidor (dígitos verificadores do CPF,
  telefone com DDD, email). Enquanto o perfil não estiver completo, o
  locador é redirecionado para ele. A mesma tela permite trocar a senha.
- **Senhas temporárias**: contas criadas pelo admin e senhas redefinidas
  por ele são provisórias — no próximo login o usuário é levado a
  `/trocar-senha` e não acessa mais nada até definir uma senha própria.
- Cadastro, edição e exclusão de imóveis (exclusão bloqueada se o imóvel
  já tiver contratos gerados), com validação de UF e CEP.
- Valor do aluguel guardado como número (`Numeric(10,2)`): o locador pode
  digitar `1500`, `1.500` ou `R$ 1.500,00` e o contrato sempre mostra
  `R$ 1.500,00`.
- Geração de contrato por link único (token), com expiração de 24h e opção
  de reenvio (só para contratos `pendente` — link já usado, assinado ou
  cancelado não é reaberto).
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
- **Verificação de integridade**: ao assinar, o locador grava o hash do
  `.docx` final (`hash_final`). A tela de visualização do contrato compara
  o arquivo em disco com o hash registrado e avisa se ele foi modificado.
- **Gravação atômica**: o `.docx` é gerado num arquivo temporário e só
  substitui o definitivo depois que o banco confirmou — uma falha no meio
  não deixa contrato "preenchido" sem arquivo nem arquivo sem registro.
- **Download em PDF**: locador e locatário recebem o contrato em PDF,
  convertido do `.docx` pelo LibreOffice. O `.docx` continua sendo o
  documento oficial (os hashes das assinaturas se referem a ele); o PDF é
  uma cópia em cache (`contratos/gerados/<token>.pdf`), refeita sempre que
  o `.docx` muda. A primeira conversão leva alguns segundos; as seguintes
  são imediatas. Se a conversão falhar, o usuário vê uma mensagem pedindo
  para tentar de novo.
- **Download público com prazo**: o locatário baixa o contrato pelo link
  público por até 7 dias após a última assinatura (o arquivo tem CPF, RG e
  endereço). O locador baixa pelo painel a qualquer momento.
- Cancelamento de contratos pendentes.
- Geração do contrato final em `.docx` a partir de um template, mesclando
  dados do locador, do imóvel, termos do contrato e dados do locatário
  (ver [Modelo de contrato](#modelo-de-contrato)).
- **Calendário de ocupação**: períodos de contratos assinados aparecem em
  vermelho e os que aguardam a assinatura do locador em amarelo, com
  tooltip mostrando imóvel e locatário ao passar o mouse.
- Confirmação em modal antes de ações destrutivas (excluir imóvel, cancelar
  contrato, desativar locador, redefinir senha) e mensagens de retorno
  após cada ação.
- **Painel administrativo**: criação de contas de locador, ativação e
  desativação de acesso (com invalidação imediata da sessão), e log de
  tentativas de login malsucedidas.
- **Segurança de login**: rate limiting (5 tentativas falhas por usuário
  ou 10 por IP em 15 minutos) e auditoria de tentativas malsucedidas.
  Cookies de sessão `HttpOnly` e `SameSite=Lax` (e `Secure` com
  `COOKIE_SECURE=1`).
- **Logs** em `instance/imofacil.log` (rotativo, 5 × 1 MB) e no stdout:
  logins, criação/cancelamento/assinatura de contratos, alterações de
  imóveis e ações do admin.
- **Datas**: gravadas em UTC no banco e exibidas/escritas no contrato no
  horário de Brasília.

## Stack

- Python 3.11, Flask, Flask-SQLAlchemy, Flask-Login, Flask-Migrate
- SQLite (arquivo em `instance/app.db`), versionado com migrações Alembic
- `python-docx` para geração dos contratos
- LibreOffice (headless) para a conversão dos contratos em PDF
- Gunicorn como servidor WSGI em produção/Docker

## Rodando localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # defina SECRET_KEY (a aplicação não sobe sem ela)
flask run
```

O download dos contratos em PDF precisa do LibreOffice instalado (comando
`soffice` no PATH) — no Debian/Ubuntu:
`sudo apt install libreoffice-writer fonts-liberation`. Sem ele, o resto
da aplicação funciona normalmente, mas o download mostra uma mensagem de erro.

A aplicação sobe em `http://127.0.0.1:5000`. No primeiro start, o banco é
criado em `instance/app.db` pelas migrações e duas contas são semeadas:

| Usuário   | Senha         | Papel   |
|-----------|---------------|---------|
| `admin`   | `admin123`    | admin   |
| `locador` | `locador123`  | locador |

Troque essas senhas em `/perfil` (ou crie novas contas de locador via painel
administrativo) antes de qualquer uso real.

## Banco de dados e migrações

A cada start, a aplicação aplica as migrações pendentes (`migrations/`) —
atualizar o código **não apaga** usuários, imóveis nem contratos. Bancos
criados antes das migrações são reconhecidos e marcados na revisão inicial
automaticamente.

Ao mudar um modelo em `models.py`, gere a migração e revise o arquivo
criado em `migrations/versions/` antes de commitar:

```bash
flask db migrate -m "descrição da mudança"
flask db upgrade
```

## Backup

```bash
flask backup                              # local
docker compose exec web flask backup      # no Docker
```

Cria `backups/<data-hora>/` com uma cópia consistente do banco (API de
backup do SQLite, segura com a aplicação no ar) e um `.zip` dos contratos
gerados. Mantém os `BACKUP_MANTER` mais recentes. Para rodar todo dia, agende
no cron do servidor, por exemplo:

```
0 3 * * * cd /caminho/do/projeto && docker compose exec -T web flask backup
```

Para restaurar: pare a aplicação, copie o `app.db` do backup para
`instance/` e extraia o `.zip` em `contratos/gerados/`.

## Esqueci a senha

- **Locador**: o admin clica em "Redefinir senha" no painel; uma senha
  temporária aparece uma única vez na tela para ser repassada.
- **Admin**: pelo terminal do servidor,
  `flask redefinir-senha admin` (ou `docker compose exec web flask redefinir-senha admin`).

## Rodando com Docker

```bash
cp .env.example .env   # defina SECRET_KEY
docker compose up -d --build
```

A aplicação sobe em `http://localhost:5000`, servida por Gunicorn. Os
volumes `./instance`, `./contratos/gerados` e `./backups` são montados no
container para persistir o banco, os contratos gerados e os backups entre
reinícios.

A imagem já inclui o LibreOffice Writer para gerar os PDFs, o que a deixa
cerca de 400 MB maior.

## Variáveis de ambiente

Lidas do ambiente ou do arquivo `.env` (veja `.env.example`).

| Variável        | Descrição                                                        | Padrão      |
|-----------------|-------------------------------------------------------------------|-------------|
| `SECRET_KEY`    | Chave de sessão do Flask. **Obrigatória** — sem ela a aplicação não sobe | —    |
| `COOKIE_SECURE` | `1` para cookies só via HTTPS (use em produção com HTTPS)          | `0`         |
| `BACKUP_MANTER` | Quantos backups o `flask backup` mantém                            | `14`        |
| `FLASK_DEBUG`   | `1` ativa o modo debug no `python app.py` (nunca em produção)      | `0`         |

## Modelo de contrato

O texto do contrato fica em `contratos/Contrato_de_Locacao_Residencial.docx`.
Para alterar cláusulas, edite o `.docx` direto — a prévia exibida ao
locatário e o contrato gerado são lidos desse mesmo arquivo.

O modelo tem o layout da marca: logo do Imofácil no cabeçalho, rodapé com
"Página X de Y", títulos das cláusulas em azul (`#1E598A`) e texto em
Arial 10,5. A formatação do texto é mantida na geração, então negrito e cores
aplicados no Word aparecem no contrato final. O bloco "Assinaturas
eletrônicas" é acrescentado pelo app (`anexar_bloco_assinaturas`) usando a
mesma cor.

Placeholders `{{campo}}` são substituídos na geração (mapa em `FIELD_MAP`,
no `app.py`):

| Origem     | Placeholders                                                                 |
|------------|-------------------------------------------------------------------------------|
| Locador    | `nome_locador`, `rg_locador`, `cpf_locador`, `email_locador`, `telefone_locador`, `endereço_locador`, `nacionalidade_locador`, `estado_locador`, `profissão_locador` |
| Locatário  | `nome_locatario`, `rg_locatario`, `cpf_locatario`, `email_locatario`, `telefone_locatario`, `endereço_locatario`, `nacionalidade_locatario`, `estado_locatario`, `profissão_locatario` |
| Imóvel     | `endereco_imovel`, `bairro_imovel`, `cidade_imovel`, `estado_imovel`, `cep_imovel` |
| Termos     | `duracao_contrato`, `data_inicio`, `data_termino`, `valor`, `forma_pagamento` |
| Data       | `dia_assinatura`, `mes` (por extenso), `ano` — data em que o locatário preenche |

Observações:

- `valor` sai sempre formatado como `R$ 1.800,00` — não escreva "R$"
  antes do placeholder no modelo.
- O foro e a cidade da assinatura usam a cidade/UF do imóvel.
- O resumo "Você se compromete a" em `templates/cliente.html` resume
  cláusulas fixas do modelo; se elas mudarem, atualize o resumo também.
- A Cláusula 13ª descreve a assinatura eletrônica feita pela própria
  plataforma (nome, documento, IP, data/hora e hash SHA-256).
- Placeholders sem mapeamento aparecem crus (`{{...}}`) tanto na prévia
  quanto no `.docx` — ao criar um novo, adicione-o ao `FIELD_MAP` e ao
  `dados_contrato`.

## Estrutura do projeto

```
app.py                  # rotas, regras de negócio e comandos (backup, redefinir-senha)
models.py                # modelos SQLAlchemy (Locador, Imovel, Contrato, Assinatura, LoginAttempt)
validacao.py             # validação de CPF, RG, telefone, email, CEP, UF e valor
migrations/              # migrações do banco (Flask-Migrate/Alembic)
templates/                # views Jinja
static/                   # CSS, JS e imagens
contratos/
  Contrato_de_Locacao_Residencial.docx   # template usado na geração e na prévia
  Contrato_Gerado.docx                    # exemplo de contrato gerado (não usado pelo app)
  gerados/                                # contratos .docx gerados e PDFs em cache (não versionado)
instance/                 # banco SQLite e log (não versionado)
backups/                  # backups gerados por "flask backup" (não versionado)
```

## Fluxo de um contrato

1. Locador (com perfil completo) cadastra o imóvel e cria um contrato
   definindo os termos → recebe um link único (`/contrato/<token>`). O
   contrato nasce `pendente`.
2. Locatário abre o link, lê o resumo e o contrato completo (com os dados
   dele aparecendo no texto enquanto digita), rola até o fim para liberar
   o aceite, preenche seus dados e aceita os termos → isso já registra a
   assinatura eletrônica dele; o `.docx` é gerado e o contrato passa a
   `preenchido`.
3. Locador revisa e assina em `/contratos/<id>/assinar` → o contrato passa
   a `assinado` e o bloco de assinaturas é anexado ao `.docx` final.
4. O período do contrato aparece no calendário de ocupação (amarelo
   enquanto `preenchido`, vermelho depois de `assinado`).

Status possíveis: `pendente` → `preenchido` → `assinado`, ou `cancelado`
(apenas a partir de `pendente`).

Links não usados em 24h expiram (`link_expirado`); o locador pode reenviar
um novo prazo a qualquer momento enquanto o contrato estiver `pendente`.
