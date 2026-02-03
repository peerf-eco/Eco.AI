"""
EcoOS Component Agent - State Definition

Определение состояния агента для генерации компонентов EcoOS.
"""

from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class ComponentSpec(BaseModel):
    """
    Спецификация компонента EcoOS из Knowledge Base.
    
    Эта структура содержит всю информацию, необходимую для генерации кода,
    работающего с компонентом.
    """
    cid: str = Field(description="Component ID, например '97322B6765B74342BBCE38798A0B40B5'")
    name: str = Field(description="Имя компонента, например 'Eco.Log1'")
    
    # Информация о фабрике (критически важно!)
    factory_export: str = Field(
        default="GetIEcoComponentFactoryPtr",
        description="Имя экспортируемой функции фабрики"
    )
    factory_signature: str = Field(
        description="Сигнатура фабрики, например 'IEcoComponentFactory* (void)'"
    )
    
    # Интерфейсы
    iid: str = Field(description="Interface ID главного интерфейса")
    interface_name: str = Field(description="Имя интерфейса, например 'IEcoLog1'")
    
    # Методы интерфейса
    methods: Dict[str, str] = Field(
        default_factory=dict,
        description="Методы: {'Info': 'void (me, char*)', ...}"
    )
    
    # Зависимости
    dependencies: List[str] = Field(
        default_factory=list,
        description="Список зависимых компонентов"
    )
    
    # Пути к файлам
    header_path: str = Field(description="Путь к заголовочному файлу интерфейса")
    id_header_path: str = Field(description="Путь к Id*.h с сигнатурой фабрики")


class GeneratedFile(BaseModel):
    """Сгенерированный файл"""
    path: str = Field(description="Путь к файлу")
    content: str = Field(description="Содержимое файла")
    file_type: str = Field(description="Тип: 'source', 'header', 'build'")


class ValidationError(BaseModel):
    """Ошибка валидации кода"""
    file: str = Field(description="Файл с ошибкой")
    line: Optional[int] = Field(default=None, description="Номер строки")
    message: str = Field(description="Описание ошибки")
    severity: str = Field(default="error", description="'error' или 'warning'")


class AgentState(TypedDict):
    """
    Состояние агента генерации компонентов EcoOS.
    
    Это главная структура данных, которая передаётся между узлами графа.
    Каждый узел читает нужные поля и обновляет свои.
    """
    
    # ═══════════════════════════════════════════════════════════════
    # ДИАЛОГ С ПОЛЬЗОВАТЕЛЕМ
    # ═══════════════════════════════════════════════════════════════
    messages: Annotated[list, add_messages]
    
    # ═══════════════════════════════════════════════════════════════
    # РЕЗУЛЬТАТ АНАЛИЗА ЗАПРОСА (Node: analyze_request)
    # ═══════════════════════════════════════════════════════════════
    user_intent: str  # "Создать калькулятор с логированием"
    required_features: List[str]  # ["arithmetic", "logging", "error_handling"]
    target_platform: str  # "windows_x64"
    app_type: str  # "console_app"
    
    # ═══════════════════════════════════════════════════════════════
    # ВЫБРАННЫЕ КОМПОНЕНТЫ (Node: select_components)
    # ═══════════════════════════════════════════════════════════════
    selected_components: List[dict]  # List[ComponentSpec.model_dump()]
    
    # ═══════════════════════════════════════════════════════════════
    # КОНТЕКСТ ИЗ RAG (Node: retrieve_context)
    # ═══════════════════════════════════════════════════════════════
    retrieved_headers: Dict[str, str]  # {component_name: header_content}
    retrieved_examples: Dict[str, str]  # {component_name: example_code}
    code_patterns: Dict[str, str]  # {"init": "шаблон инициализации", ...}
    
    # ═══════════════════════════════════════════════════════════════
    # СГЕНЕРИРОВАННЫЙ КОД (Node: generate_code)
    # ═══════════════════════════════════════════════════════════════
    generated_files: List[dict]  # List[GeneratedFile.model_dump()]
    
    # ═══════════════════════════════════════════════════════════════
    # РЕЗУЛЬТАТ ПРОВЕРКИ (Node: review_code)
    # ═══════════════════════════════════════════════════════════════
    validation_errors: List[dict]  # List[ValidationError.model_dump()]
    is_valid: bool  # True если код прошёл проверку
    
    # ═══════════════════════════════════════════════════════════════
    # УПРАВЛЕНИЕ ИТЕРАЦИЯМИ
    # ═══════════════════════════════════════════════════════════════
    iteration_count: int  # Текущая итерация (макс 3)
    max_iterations: int  # Максимум итераций

