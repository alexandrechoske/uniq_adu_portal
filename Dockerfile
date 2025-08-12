# site/Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependências do sistema (se seu app precisar de algo como libpq-dev, etc., adicione aqui)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Instale requirements
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copie o projeto
COPY . /app

# Se usar .env, o compose passará via env_file; nada a expor aqui
EXPOSE 8000

# Suba com gunicorn (troque app:app se o módulo/variável mudar)
CMD ["gunicorn", "-w", "3", "-k", "gthread", "--threads", "8", "--timeout", "120", "-b", "0.0.0.0:8000", "app:app"]

