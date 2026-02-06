#!/usr/bin/env python3
"""
Инициализация CodeRAG системы через OpenRouter API

Создает векторное хранилище ChromaDB
Использует семантический чанкинг для C/C++ кода

Использование:
    python scripts/init_rag.py

Переменные окружения (из .env):
    RAG_STORAGE - путь к директории с исходниками
    CHROMA_DB - путь к ChromaDB
    EMBEDDINGS_MODEL - модель для эмбеддингов (через OpenRouter)
    OPENROUTER_URL - URL OpenRouter API
    OPENAI_API_KEY - API ключ OpenRouter
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

# Настройки
RAG_STORAGE = os.getenv("RAG_STORAGE", "./rag_storage")
CHROMA_DB = os.getenv("CHROMA_DB", "./chroma_db")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "qwen/qwen3-embedding-8b")
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
API_KEY = os.getenv("OPENAI_API_KEY")


def main():
    print("=" * 70)
    print("  EcoOS Component Agent - CodeRAG Initialization")
    print("  Using OpenRouter API for embeddings")
    print("=" * 70)
    print()
    print(f"[CONFIG] RAG storage: {RAG_STORAGE}")
    print(f"[CONFIG] ChromaDB path: {CHROMA_DB}")
    print(f"[CONFIG] Embeddings model: {EMBEDDINGS_MODEL}")
    print(f"[CONFIG] OpenRouter URL: {OPENROUTER_URL}")
    print()

    # Проверка API ключа
    if not API_KEY:
        print("[ERROR] OPENAI_API_KEY not set in .env")
        print("[INFO] Get your key at https://openrouter.ai/keys")
        sys.exit(1)

    # Проверка наличия rag_storage
    if not Path(RAG_STORAGE).exists():
        print(f"[ERROR] RAG storage not found: {RAG_STORAGE}")
        print("[INFO] Please populate rag_storage with source files first")
        sys.exit(1)

    # Подсчет файлов
    source_files = list(Path(RAG_STORAGE).rglob("*.[ch]")) + \
                   list(Path(RAG_STORAGE).rglob("*.hpp")) + \
                   list(Path(RAG_STORAGE).rglob("*.cpp"))
    
    if not source_files:
        print(f"[ERROR] No source files found in: {RAG_STORAGE}")
        sys.exit(1)
    
    print(f"[INFO] Found {len(source_files)} source files")
    print()

    # Импорты
    print("[INFO] Loading dependencies...")
    
    try:
        from langchain_openai import OpenAIEmbeddings
        from langchain_community.document_loaders import DirectoryLoader, TextLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_chroma import Chroma
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("[INFO] Run: pip install langchain-openai langchain-community langchain-chroma chromadb")
        sys.exit(1)

    # Инициализация эмбеддингов через OpenRouter API
    print(f"[INFO] Connecting to OpenRouter embeddings API...")
    print(f"[INFO] Model: {EMBEDDINGS_MODEL}")
    print()

    try:
        embeddings = OpenAIEmbeddings(
            model=EMBEDDINGS_MODEL,
            openai_api_key=API_KEY,
            openai_api_base=OPENROUTER_URL,
        )
        print("[INFO] OpenRouter connection established")
        print()
    except Exception as e:
        print(f"[ERROR] Failed to connect to OpenRouter: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Загрузка документов
    print("[INFO] Loading documents from rag_storage...")
    print()

    try:
        all_docs = []
        
        for ext in ['*.h', '*.hpp', '*.c', '*.cpp']:
            loader = DirectoryLoader(
                RAG_STORAGE,
                glob=f"**/{ext}",
                loader_cls=TextLoader,
                loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
                recursive=True,
                show_progress=True,
                silent_errors=True
            )
            docs = loader.load()
            all_docs.extend(docs)
            print(f"[INFO] Loaded {len(docs)} {ext} files")
        
        print(f"[INFO] Total documents loaded: {len(all_docs)}")
        print()
        
    except Exception as e:
        print(f"[ERROR] Failed to load documents: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    if not all_docs:
        print("[ERROR] No documents loaded!")
        sys.exit(1)

    # Семантический чанкинг для C/C++ кода
    print("[INFO] Splitting documents into semantic chunks...")
    print()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=[
            "\n\n",
            "typedef struct",
            "typedef enum",
            "interface ",
            "#define",
            "ECO_EXPORT",
            "ECOCALLMETHOD",
            "/*",
            "\n",
        ],
        length_function=len,
        is_separator_regex=False,
    )

    try:
        chunks = text_splitter.split_documents(all_docs)
        print(f"[INFO] Created {len(chunks)} chunks")
        print()
    except Exception as e:
        print(f"[ERROR] Failed to split documents: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Добавление метаданных
    print("[INFO] Adding metadata to chunks...")
    print()

    for i, chunk in enumerate(chunks):
        source = chunk.metadata.get("source", "")
        
        if source:
            path_parts = Path(source).parts
            component = "unknown"
            for part in path_parts:
                if "Eco." in part:
                    component = part
                    break
            
            file_name = Path(source).name
            file_ext = Path(source).suffix
        else:
            component = "unknown"
            file_name = "unknown"
            file_ext = ""
        
        # Определяем тип чанка
        content_lower = chunk.page_content.lower()
        if "typedef struct" in content_lower:
            chunk_type = "struct"
        elif "interface " in content_lower or "vtbl" in content_lower:
            chunk_type = "interface"
        elif "#define" in chunk.page_content:
            chunk_type = "macro"
        elif "eco_export" in content_lower:
            chunk_type = "export"
        else:
            chunk_type = "code"
        
        breadcrumb = f"{component} > {file_name} > {chunk_type}"
        
        chunk.metadata.update({
            "component": component,
            "file_name": file_name,
            "file_type": file_ext,
            "breadcrumb": breadcrumb,
            "chunk_index": i,
            "chunk_type": chunk_type
        })

    # Создание векторного хранилища
    print("[INFO] Creating ChromaDB vector store...")
    print(f"[INFO] This will generate embeddings for {len(chunks)} chunks via OpenRouter API...")
    print("[INFO] This may take a while depending on the number of chunks...")
    print()

    try:
        # Удаляем старую базу если есть
        if Path(CHROMA_DB).exists():
            import shutil
            print(f"[INFO] Removing old ChromaDB at: {CHROMA_DB}")
            shutil.rmtree(CHROMA_DB)
        
        # Создаем новую базу
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=CHROMA_DB,
            collection_name="ecoos_components",
        )
        
        print()
        print("=" * 70)
        print("  SUCCESS!")
        print("=" * 70)
        print(f"[INFO] Vector store created successfully!")
        print(f"[INFO] Total chunks indexed: {len(chunks)}")
        print(f"[INFO] ChromaDB persisted to: {CHROMA_DB}")
        print()
        print("[INFO] You can now run the agent:")
        print("       python -m agent.main 'Создай калькулятор'")
        print()
        
    except Exception as e:
        print(f"[ERROR] Failed to create vector store: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
