# EcoOS Component Agent - CodeRAG with Qwen3-Embedding-8B
# 
# Использует:
# - Qwen3-Embedding-8B (4096 dimensions)
# - ChromaDB для векторного хранилища
# - LangChain для RAG pipeline
# - OpenRouter для LLM

FROM python:3.11-slim

# Метаданные
LABEL maintainer="EcoOS Agent"
LABEL description="CodeRAG agent with Qwen3-Embedding-8B and ChromaDB"

# Переменные окружения (значения по умолчанию, переопределяются из .env)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    RAG_STORAGE=/app/rag_storage \
    CHROMA_DB=/app/chroma_db

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование requirements
COPY agent/requirements.txt /app/requirements.txt

# Установка Python зависимостей из requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Создание директорий для данных
RUN mkdir -p /app/rag_storage \
    /app/chroma_db \
    /app/output

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
echo "[INFO] RAG Storage: $RAG_STORAGE"\n\
echo "[INFO] ChromaDB: $CHROMA_DB"\n\
echo ""\n\
\n\
# Проверка наличия ChromaDB\n\
if [ ! -d "$CHROMA_DB" ] || [ -z "$(ls -A $CHROMA_DB 2>/dev/null)" ]; then\n\
    echo "[WARN] ChromaDB not found or empty."\n\
    echo "[INFO] Run: docker-compose run ecagos-agent init-rag"\n\
fi\n\
\n\
# Запуск команды\n\
if [ "$1" = "init-rag" ]; then\n\
    echo "[INFO] Initializing RAG system..."\n\
    python /app/scripts/init_rag.py\n\
elif [ "$1" = "agent" ]; then\n\
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
