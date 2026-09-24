FROM python:3.11-slim

WORKDIR /app

# LibreOffice (só o Writer, sem interface) converte o contrato .docx em PDF
# para download; as fontes Liberation substituem Arial/Times do template.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libreoffice-writer-nogui fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p instance contratos/gerados backups

# Permite rodar "flask backup", "flask db ..." e "flask redefinir-senha" no container.
ENV FLASK_APP=app

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
