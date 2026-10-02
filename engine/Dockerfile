# syntax=docker/dockerfile:1.7
# @spec docs/BACKLOG.md#RG-018 | docs/DAT.md#deploiement
# Image du moteur RGPD Guard (CPU uniquement). Cibles : dev (dépendances de test, code monté) et prod (modèles intégrés).
# Le secret de construction « ca » (facultatif, vide par défaut) permet de construire derrière un proxy TLS.

ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1

FROM base AS deps
RUN --mount=type=secret,id=ca,required=false \
    sh -c 'if [ -s /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi; pip install --no-cache-dir uv==0.12.*'
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN --mount=type=secret,id=ca,required=false --mount=type=cache,target=/root/.cache/uv \
    sh -c 'if [ -s /run/secrets/ca ]; then export SSL_CERT_FILE=/run/secrets/ca; fi; \
    uv sync --frozen --no-dev --no-install-project --extra nlp --extra laya --extra gliner'

FROM deps AS dev-deps
RUN --mount=type=secret,id=ca,required=false --mount=type=cache,target=/root/.cache/uv \
    sh -c 'if [ -s /run/secrets/ca ]; then export SSL_CERT_FILE=/run/secrets/ca; fi; \
    uv sync --frozen --group dev --no-install-project --extra nlp --extra laya --extra gliner'

FROM base AS models
COPY --from=deps /opt/venv /opt/venv
COPY rgpd_guard/model_store.py /tmp/model_store.py
RUN --mount=type=secret,id=ca,required=false \
    sh -c 'if [ -s /run/secrets/ca ]; then export SSL_CERT_FILE=/run/secrets/ca REQUESTS_CA_BUNDLE=/run/secrets/ca; fi; \
    /opt/venv/bin/python /tmp/model_store.py /models'

FROM base AS runtime
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin rgpd \
    && mkdir -p /data /models \
    && chown rgpd:rgpd /data
ENV PATH=/opt/venv/bin:$PATH \
    HF_HOME=/models \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    RGPD_GUARD_DATA_DIR=/data \
    RGPD_GUARD_MODELS_DIR=/models
WORKDIR /app
EXPOSE 8742
HEALTHCHECK --interval=10s --timeout=5s --start-period=180s --retries=6 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8742/health', timeout=3)"
CMD ["python", "-m", "rgpd_guard"]

FROM runtime AS dev
# curl sert aux tests de contrat du client de hook exécutés dans le conteneur.
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=dev-deps /opt/venv /opt/venv
COPY . /app
USER rgpd

FROM runtime AS prod
COPY --from=deps /opt/venv /opt/venv
COPY --from=models /models /models
COPY rgpd_guard /app/rgpd_guard
USER rgpd
