"""
EcoOS Knowledge Base

══════════════════════════════════════════════════════════════════════════════
ЗАГЛУШКА для Knowledge Base

Сейчас это статические данные. Для полноценной системы нужно:

1. СТРУКТУРА ДАННЫХ:
   knowledge_base/
   ├── components/           # YAML-файлы с метаданными компонентов
   │   ├── index.yaml        # Реестр всех компонентов
   │   └── Eco.Log1.yaml     # Спецификация каждого компонента
   │
   ├── headers/              # Заголовочные файлы (копия из SDK)
   │   ├── Eco.Core1/
   │   └── Eco.InterfaceBus1/
   │
   ├── examples/             # Примеры использования
   │   ├── basic_init.c
   │   └── logging_example.c
   │
   └── chroma_db/            # Векторная база (ChromaDB)

2. СОЗДАНИЕ ИНДЕКСА:
   ```python
   from langchain_community.document_loaders import DirectoryLoader
   from langchain_chroma import Chroma
   from langchain_openai import OpenAIEmbeddings
   
   # Загрузить все .h файлы
   loader = DirectoryLoader("source-code/", glob="**/*.h")
   docs = loader.load()
   
   # Создать векторное хранилище
   vectorstore = Chroma.from_documents(
       docs, 
       OpenAIEmbeddings(),
       persist_directory="./knowledge_base/chroma_db"
   )
   ```

3. ПОИСК:
   ```python
   results = vectorstore.similarity_search(
       "IEcoLog1 Info method signature",
       k=3
   )
   ```

══════════════════════════════════════════════════════════════════════════════
"""

from .components import (
    FEATURE_TO_COMPONENTS,
    COMPONENTS_REGISTRY,
    get_component_spec,
    get_header_content,
    get_example_code,
    get_code_pattern,
)

__all__ = [
    "FEATURE_TO_COMPONENTS",
    "COMPONENTS_REGISTRY",
    "get_component_spec",
    "get_header_content",
    "get_example_code",
    "get_code_pattern",
]

