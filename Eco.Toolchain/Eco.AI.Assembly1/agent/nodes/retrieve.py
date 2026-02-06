"""
Node: retrieve_context

Извлекает контекст из Knowledge Base (ChromaDB):
- Заголовочные файлы (*.h) с интерфейсами и сигнатурами
- Примеры использования компонентов
- Шаблоны кода

Использует ChromaDB для семантического поиска.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path


def get_vectorstore():
    """
    Получает векторное хранилище ChromaDB.
    
    Использует OpenRouter API для эмбеддингов.
    
    Returns:
        Chroma vectorstore или None если не инициализирован
    """
    chroma_db_path = os.getenv("CHROMA_DB", "./chroma_db")
    
    if not Path(chroma_db_path).exists():
        print(f"[RETRIEVE] [WARN] ChromaDB not found at: {chroma_db_path}")
        print("[RETRIEVE] [WARN] Run 'python scripts/init_rag.py' to initialize RAG")
        return None
    
    try:
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings
        
        embeddings_model = os.getenv("EMBEDDINGS_MODEL", "qwen/qwen3-embedding-8b")
        openrouter_url = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            print("[RETRIEVE] [ERROR] OPENAI_API_KEY not set")
            return None
        
        print(f"[RETRIEVE] Using OpenRouter embeddings: {embeddings_model}")
        
        embeddings = OpenAIEmbeddings(
            model=embeddings_model,
            openai_api_key=api_key,
            openai_api_base=openrouter_url,
        )
        
        vectorstore = Chroma(
            persist_directory=chroma_db_path,
            embedding_function=embeddings,
            collection_name="ecoos_components"
        )
        
        print(f"[RETRIEVE] ChromaDB loaded from: {chroma_db_path}")
        return vectorstore
        
    except Exception as e:
        print(f"[RETRIEVE] [ERROR] Failed to load ChromaDB: {e}")
        return None


def search_headers(vectorstore, component_name: str, k: int = 5) -> str:
    """
    Ищет заголовочные файлы для компонента.
    
    Args:
        vectorstore: ChromaDB vectorstore
        component_name: Имя компонента (e.g., "Eco.InterfaceBus1")
        k: Количество результатов
        
    Returns:
        Объединённое содержимое найденных заголовков
    """
    query = f"interface {component_name} methods signature header"
    
    try:
        results = vectorstore.similarity_search(
            query,
            k=k,
            filter={"component": {"$contains": component_name.split('.')[-1]}}
        )
        
        if not results:
            # Пробуем без фильтра
            results = vectorstore.similarity_search(query, k=k)
        
        return "\n\n".join([doc.page_content for doc in results])
        
    except Exception as e:
        print(f"[RETRIEVE] [WARN] Search failed for {component_name}: {e}")
        return ""


def search_examples(vectorstore, component_name: str, k: int = 3) -> str:
    """
    Ищет примеры использования компонента.
    
    Args:
        vectorstore: ChromaDB vectorstore
        component_name: Имя компонента
        k: Количество результатов
        
    Returns:
        Объединённые примеры
    """
    query = f"{component_name} usage example code initialization"
    
    try:
        results = vectorstore.similarity_search(query, k=k)
        return "\n\n".join([doc.page_content for doc in results])
    except Exception as e:
        print(f"[RETRIEVE] [WARN] Example search failed for {component_name}: {e}")
        return ""


def retrieve_context(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Извлекает контекст из Knowledge Base для выбранных компонентов.
    
    Это КЛЮЧЕВОЙ узел для генерации корректного кода!
    Здесь мы получаем:
    - Точные сигнатуры функций из заголовков
    - Примеры правильного использования
    - Шаблоны типовых операций
    
    Args:
        state: Текущее состояние с selected_components
        
    Returns:
        retrieved_headers, retrieved_examples, code_patterns
    """
    
    print("[RETRIEVE] Starting context retrieval...")
    
    selected_components = state.get("selected_components", [])
    print(f"[RETRIEVE] Components to retrieve: {len(selected_components)}")
    
    headers = {}
    examples = {}
    
    # Пробуем загрузить ChromaDB
    vectorstore = get_vectorstore()
    
    if vectorstore:
        # Используем RAG для поиска
        print("[RETRIEVE] Using ChromaDB for retrieval")
        
        for comp in selected_components:
            name = comp["name"]
            
            # Ищем заголовки
            header_content = search_headers(vectorstore, name)
            if header_content:
                headers[name] = header_content
                print(f"[RETRIEVE] Found headers for: {name}")
            
            # Ищем примеры
            example_content = search_examples(vectorstore, name)
            if example_content:
                examples[name] = example_content
                print(f"[RETRIEVE] Found examples for: {name}")
    
    else:
        # Fallback на статические данные из knowledge_base
        print("[RETRIEVE] ChromaDB not available, using static fallback")
        
        from ..knowledge_base import (
            get_header_content,
            get_example_code,
        )
        
        for comp in selected_components:
            name = comp["name"]
            
            # Загружаем заголовочный файл интерфейса
            header = get_header_content(comp.get("header_path", ""))
            if header:
                headers[name] = header
                print(f"[RETRIEVE] Loaded static header for: {name}")
            
            # Загружаем Id*.h - там сигнатура фабрики!
            id_header = get_header_content(comp.get("id_header_path", ""))
            if id_header:
                headers[f"{name}_Id"] = id_header
                print(f"[RETRIEVE] Loaded static Id header for: {name}")
            
            # Загружаем примеры
            example = get_example_code(name)
            if example:
                examples[name] = example
                print(f"[RETRIEVE] Loaded static example for: {name}")
    
    # Загружаем общие шаблоны кода (всегда из статики)
    from ..knowledge_base import get_code_pattern
    
    patterns = {
        "factory_load": get_code_pattern("factory_load"),
        "component_init": get_code_pattern("component_init"),
        "error_handling": get_code_pattern("error_handling"),
        "cleanup": get_code_pattern("cleanup"),
    }
    
    print(f"[RETRIEVE] Total headers: {len(headers)}")
    print(f"[RETRIEVE] Total examples: {len(examples)}")
    print(f"[RETRIEVE] Total patterns: {len([p for p in patterns.values() if p])}")
    
    return {
        "retrieved_headers": headers,
        "retrieved_examples": examples,
        "code_patterns": patterns,
    }
