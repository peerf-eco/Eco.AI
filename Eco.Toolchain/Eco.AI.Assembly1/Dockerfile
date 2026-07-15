# EcoOS Component Agent (V7) — backend API + agent
#
# Stack: FastAPI + custom Orchestrator + pi_ai (OpenRouter) + sqlite-vec RAG.
# No ChromaDB / LangChain (retired 2026-06-22).
#
# Base image is digest-pinned for reproducibility. To refresh the pin:
#   docker buildx imagetools inspect python:3.11-slim
FROM python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5

LABEL maintainer="EcoOS Agent"
LABEL description="EcoOS V7 agent — FastAPI + pi_ai + sqlite-vec RAG"

# Переменные окружения (значения по умолчанию, переопределяются из .env)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Установка системных зависимостей
# wine64: запуск Windows-only eco-cli.exe из Linux-контейнера. Нативной
# Linux-сборки eco-cli (GraalVM native-image + AWS CRT JNI) не существует —
# wine — единственный практичный способ оставить весь стек в одной compose
# схеме. Преинициализация WINEPREFIX в build-time убирает 10-30с лаг при
# первом вызове и гарантирует, что wineboot не пишет в read-only volume.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    wine64 \
    && rm -rf /var/lib/apt/lists/*

ENV WINEPREFIX=/tmp/wine \
    WINEDEBUG=-all
# Debian 13 trixie ships wine64 binary at /usr/lib/wine/wine64 and does NOT
# install a wrapper in PATH. Symlink it so subprocess calls that don't go
# through V6_CLI_PREFIX (and any future debug shells) still work.
RUN ln -sf /usr/lib/wine/wine64 /usr/bin/wine \
    && mkdir -p /tmp/wine \
    && /usr/lib/wine/wine64 wineboot -i 2>/dev/null || true

# Рабочая директория
WORKDIR /app

# Python deps: install from the compiled lock, not the >= ranges in
# requirements.txt. The lock is the reproducibility guarantee; regenerate it
# after editing requirements.txt:
#   uv pip compile requirements.txt --python-version 3.11 \
#       --python-platform x86_64-unknown-linux-gnu -o requirements.lock
COPY agent/requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.lock

# Создание директорий для данных
RUN mkdir -p /app/output

# Копирование кода агента
COPY agent/ /app/agent/
COPY backend/ /app/backend/
COPY scripts/ /app/scripts/

# Создание entrypoint скрипта
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "========================================"\n\
echo "  EcoOS Component Agent"\n\
echo "  LLM: $LLM_MODEL"\n\
echo "  Embeddings: $EMBEDDINGS_MODEL"\n\
echo "========================================"\n\
echo ""\n\
\n\
# Проверка переменных окружения\n\
if [ -z "$OPENAI_API_KEY" ]; then\n\
    echo "[ERROR] OPENAI_API_KEY not set!"\n\
    echo "[INFO] Set it in .env file or pass as environment variable"\n\
    exit 1\n\
fi\n\
\n\
echo "[INFO] API URL: $OPENROUTER_URL"\n\
echo ""\n\
\n\
# Запуск команды\n\
if [ "$1" = "agent" ]; then\n\
    shift\n\
    python -m agent.main "$@"\n\
elif [ "$1" = "shell" ]; then\n\
    /bin/bash\n\
else\n\
    exec "$@"\n\
fi\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# По умолчанию запускаем агента с помощью
CMD ["agent", "--help"]
