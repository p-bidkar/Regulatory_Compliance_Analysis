FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf_cache

WORKDIR /app

# build-essential covers native-extension wheels (e.g. hnswlib/chromadb) that
# don't ship prebuilt wheels for every platform.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so this layer is cached across code-only changes.
COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip && pip install -e .

COPY apps ./apps
COPY scripts ./scripts
COPY data ./data
COPY report ./report

RUN mkdir -p /app/chroma_db /app/.hf_cache

EXPOSE 8501

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["streamlit", "run", "apps/streamlit_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
