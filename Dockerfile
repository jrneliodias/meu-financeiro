# Build stage - instala dependencias
FROM python:3.10.5-slim as builder

WORKDIR /app

# Instala dependencias de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Production stage
FROM python:3.10.5-slim

# Configura locale brasileiro
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    libpq5 \
    curl \
    && locale-gen pt_BR.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=pt_BR.UTF-8
ENV LC_ALL=pt_BR.UTF-8

# Cria usuario nao-root
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Instala dependencias do stage anterior
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/* && rm -rf /wheels

# Copia codigo da aplicacao
COPY --chown=appuser:appuser . .

# Cria diretorio para static files
RUN mkdir -p /app/staticfiles && chown appuser:appuser /app/staticfiles

# Troca para usuario nao-root
USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Inicia com Gunicorn
CMD ["gunicorn", "finance.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
