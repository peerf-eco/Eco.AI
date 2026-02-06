"""
EcoOS Components Registry

Реестр компонентов EcoOS с их спецификациями.

══════════════════════════════════════════════════════════════════════════════
ЗАГЛУШКА: Захардкоженные данные

В реальной системе это должно:
1. Загружаться из YAML-файлов
2. Индексироваться в векторную базу
3. Обновляться при изменении SDK
══════════════════════════════════════════════════════════════════════════════
"""

from typing import Optional, Dict
from ..state import ComponentSpec


# ═══════════════════════════════════════════════════════════════════════════
# МАППИНГ: Фича → Компоненты
# ═══════════════════════════════════════════════════════════════════════════

FEATURE_TO_COMPONENTS: Dict[str, list] = {
    "component_bus": ["Eco.InterfaceBus1"],
    "logging": ["Eco.Log1"],
    "arithmetic": [],  # Реализуется в приложении, не требует компонентов
    "file_io": ["Eco.FileSystemManagement1"],
    "memory_management": ["Eco.MemoryManager1"],
    "string_operations": ["Eco.String1"],
    "error_handling": ["Eco.Error1"],
    "networking": ["Eco.Network1"],
}


# ═══════════════════════════════════════════════════════════════════════════
# РЕЕСТР КОМПОНЕНТОВ
# ═══════════════════════════════════════════════════════════════════════════

COMPONENTS_REGISTRY: Dict[str, ComponentSpec] = {
    
    # ───────────────────────────────────────────────────────────────────────
    # Eco.InterfaceBus1 - Шина компонентов (ОБЯЗАТЕЛЬНЫЙ)
    # ───────────────────────────────────────────────────────────────────────
    "Eco.InterfaceBus1": ComponentSpec(
        cid="00000000000000000000000042757331",
        name="Eco.InterfaceBus1",
        
        # КРИТИЧЕСКИ ВАЖНО: правильная сигнатура фабрики!
        factory_export="GetIEcoComponentFactoryPtr",
        factory_signature="IEcoComponentFactory* ECOCALLMETHOD (void)",
        
        iid="00000000-0000-0000-0000-A00000000101",
        interface_name="IEcoInterfaceBus1",
        
        methods={
            "Init": "int16_t (IEcoInterfaceBus1Ptr_t me)",
            "InitWith": "int16_t (IEcoInterfaceBus1Ptr_t me, void* heapStartAddress, uint32_t size)",
            "RegisterComponent": "int16_t (IEcoInterfaceBus1Ptr_t me, const UGUID* rcid, IEcoUnknownPtr_t pIFactory)",
            "UnRegisterComponent": "int16_t (IEcoInterfaceBus1Ptr_t me, const UGUID* rcid)",
            "QueryComponent": "int16_t (IEcoInterfaceBus1Ptr_t me, const UGUID* rcid, IEcoUnknownPtr_t pIUnkOuter, const UGUID* riid, voidptr_t* ppv)",
        },
        
        dependencies=[],
        
        header_path="source-code/Eco.InterfaceBus1/SharedFiles/IEcoInterfaceBus1.h",
        id_header_path="source-code/Eco.InterfaceBus1/SharedFiles/IdEcoInterfaceBus1.h",
    ),
    
    # ───────────────────────────────────────────────────────────────────────
    # Eco.Log1 - Логирование
    # ───────────────────────────────────────────────────────────────────────
    "Eco.Log1": ComponentSpec(
        cid="97322B6765B74342BBCE38798A0B40B5",
        name="Eco.Log1",
        
        factory_export="GetIEcoComponentFactoryPtr",
        factory_signature="IEcoComponentFactory* ECOCALLMETHOD (void)",
        
        iid="F3B19793-BD14-4E9F-B7EA-64EDF4B6453F",
        interface_name="IEcoLog1",
        
        methods={
            "set_LevelMask": "void (IEcoLog1Ptr_t me, uint16_t mask)",
            "get_LevelMask": "uint16_t (IEcoLog1Ptr_t me)",
            "Debug": "void (IEcoLog1Ptr_t me, char_t* message)",
            "Info": "void (IEcoLog1Ptr_t me, char_t* message)",
            "Warn": "void (IEcoLog1Ptr_t me, char_t* message)",
            "Error": "void (IEcoLog1Ptr_t me, char_t* message)",
            "Fatal": "void (IEcoLog1Ptr_t me, char_t* message)",
        },
        
        dependencies=["Eco.InterfaceBus1"],
        
        header_path="source-code/Eco.Log1/SharedFiles/IEcoLog1.h",
        id_header_path="source-code/Eco.Log1/SharedFiles/IdEcoLog1.h",
    ),
    
    # ───────────────────────────────────────────────────────────────────────
    # TODO: Добавить остальные компоненты
    # ───────────────────────────────────────────────────────────────────────
    # "Eco.MemoryManager1": ComponentSpec(...),
    # "Eco.FileSystemManagement1": ComponentSpec(...),
    # "Eco.String1": ComponentSpec(...),
}


# ═══════════════════════════════════════════════════════════════════════════
# ФУНКЦИИ ДОСТУПА К ДАННЫМ
# ═══════════════════════════════════════════════════════════════════════════

def get_component_spec(name: str) -> Optional[ComponentSpec]:
    """
    Получить спецификацию компонента по имени.
    
    В реальной системе:
    - Сначала искать в кэше
    - Потом в YAML-файлах
    - Потом в векторной базе
    """
    return COMPONENTS_REGISTRY.get(name)


def get_header_content(path: str) -> Optional[str]:
    """
    Получить содержимое заголовочного файла.
    
    ════════════════════════════════════════════════════════════════════════
    ЗАГЛУШКА: Возвращает захардкоженные заголовки
    
    В реальной системе:
    1. Читать файл с диска: open(path).read()
    2. Или искать в векторной базе по пути
    ════════════════════════════════════════════════════════════════════════
    """
    
    # Захардкоженные заголовки для примера
    HEADERS = {
        "source-code/Eco.InterfaceBus1/SharedFiles/IEcoInterfaceBus1.h": '''
/* IEcoInterfaceBus1.h */
#ifndef __I_ECO_INTERFACE_BUS_1_H__
#define __I_ECO_INTERFACE_BUS_1_H__

#include "IEcoBase1.h"

/* IEcoInterfaceBus1 IID = {00000000-0000-0000-0000-A00000000101} */
static const UGUID IID_IEcoInterfaceBus1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xA0, 0x00, 0x00, 0x00, 0x01, 0x01} };

typedef struct IEcoInterfaceBus1* IEcoInterfaceBus1Ptr_t;

typedef struct IEcoInterfaceBus1VTbl {
    /* IEcoUnknown */
    int16_t (ECOCALLMETHOD *QueryInterface)(IEcoInterfaceBus1Ptr_t me, const UGUID* riid, voidptr_t* ppv);
    uint32_t (ECOCALLMETHOD *AddRef)(IEcoInterfaceBus1Ptr_t me);
    uint32_t (ECOCALLMETHOD *Release)(IEcoInterfaceBus1Ptr_t me);

    /* IEcoInterfaceBus1 */
    int16_t (ECOCALLMETHOD *Init)(IEcoInterfaceBus1Ptr_t me);
    int16_t (ECOCALLMETHOD *RegisterComponent)(IEcoInterfaceBus1Ptr_t me, const UGUID* rcid, IEcoUnknownPtr_t pIFactory);
    int16_t (ECOCALLMETHOD *QueryComponent)(IEcoInterfaceBus1Ptr_t me, const UGUID* rcid, IEcoUnknownPtr_t pIUnkOuter, const UGUID* riid, voidptr_t* ppv);
} IEcoInterfaceBus1VTbl;

interface IEcoInterfaceBus1 {
    struct IEcoInterfaceBus1VTbl *pVTbl;
};

#endif
''',
        
        "source-code/Eco.InterfaceBus1/SharedFiles/IdEcoInterfaceBus1.h": '''
/* IdEcoInterfaceBus1.h */
#ifndef __ID_ECO_INTERFACE_BUS_1_H__
#define __ID_ECO_INTERFACE_BUS_1_H__

#include "IEcoInterfaceBus1.h"

/* EcoInterfaceBus1 CID = {00000000-0000-0000-0000-000042757331} */
static const UGUID CID_EcoInterfaceBus1 = { 0x01, 0x10, {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x42, 0x75, 0x73, 0x31} };

/* 
 * ВАЖНО: Функция возвращает указатель НАПРЯМУЮ!
 * НЕ через out-параметр!
 */
#ifdef ECO_DLL
ECO_EXPORT IEcoComponentFactory* ECOCALLMETHOD GetIEcoComponentFactoryPtr();
#endif

#endif
''',
    }
    
    return HEADERS.get(path)


def get_example_code(component_name: str) -> Optional[str]:
    """
    Получить пример использования компонента.
    
    ════════════════════════════════════════════════════════════════════════
    ЗАГЛУШКА: Возвращает захардкоженные примеры
    
    В реальной системе:
    1. Искать в папке examples/ по имени компонента
    2. Или использовать векторный поиск: "example usage of {component_name}"
    ════════════════════════════════════════════════════════════════════════
    """
    
    EXAMPLES = {
        "Eco.InterfaceBus1": '''
/* Пример инициализации InterfaceBus1 */

#include "IdEcoInterfaceBus1.h"

int main() {
    IEcoInterfaceBus1* pIBus = 0;
    IEcoComponentFactory* pFactory = 0;
    int16_t result;
    
    /* 1. Получаем фабрику - возвращает указатель НАПРЯМУЮ! */
    pFactory = GetIEcoComponentFactoryPtr();
    if (pFactory == 0) {
        printf("Error: Failed to get factory\\n");
        return -1;
    }
    
    /* 2. Создаём экземпляр через Alloc */
    result = pFactory->pVTbl->Alloc(
        pFactory,
        0,  /* pISystem */
        0,  /* pIUnknownOuter */
        &IID_IEcoInterfaceBus1,
        (voidptr_t*)&pIBus
    );
    
    if (result != ERR_ECO_OK || pIBus == 0) {
        printf("Error: Failed to create instance\\n");
        return -1;
    }
    
    /* 3. Инициализируем шину */
    result = pIBus->pVTbl->Init(pIBus);
    
    /* ... использование ... */
    
    /* 4. Освобождаем ресурсы */
    pIBus->pVTbl->Release(pIBus);
    
    return 0;
}
''',
        
        "Eco.Log1": '''
/* Пример использования Eco.Log1 */

#include "IEcoLog1.h"

void use_logger(IEcoLog1* pILog) {
    /* Устанавливаем маску уровней */
    pILog->pVTbl->set_LevelMask(pILog, 0xFFFF);  /* Все уровни */
    
    /* Логирование */
    pILog->pVTbl->Debug(pILog, "Debug message");
    pILog->pVTbl->Info(pILog, "Info message");
    pILog->pVTbl->Warn(pILog, "Warning message");
    pILog->pVTbl->Error(pILog, "Error message");
}
''',
    }
    
    return EXAMPLES.get(component_name)


def get_code_pattern(pattern_name: str) -> Optional[str]:
    """
    Получить шаблон кода.
    
    Шаблоны - это типовые паттерны для:
    - Загрузки компонентов
    - Обработки ошибок
    - Освобождения ресурсов
    """
    
    PATTERNS = {
        "factory_load": '''
/* Шаблон загрузки фабрики компонента */
IEcoComponentFactory* pFactory = GetIEcoComponentFactoryPtr();
if (pFactory == 0) {
    /* Обработка ошибки */
}
''',
        
        "component_init": '''
/* Шаблон создания и инициализации компонента */
int16_t result = pFactory->pVTbl->Alloc(
    pFactory,
    pISystem,       /* Системный интерфейс или 0 */
    0,              /* pIUnknownOuter для агрегации */
    &IID_Interface, /* IID требуемого интерфейса */
    (voidptr_t*)&pInstance
);

if (result != ERR_ECO_OK || pInstance == 0) {
    /* Обработка ошибки */
}
''',
        
        "error_handling": '''
/* Шаблон обработки ошибок EcoOS */
if (result != ERR_ECO_OK) {
    printf("Error: 0x%04X\\n", result);
    /* Освободить уже выделенные ресурсы */
    goto cleanup;
}
''',
        
        "cleanup": '''
/* Шаблон освобождения ресурсов */
cleanup:
    if (pInstance) {
        pInstance->pVTbl->Release(pInstance);
        pInstance = 0;
    }
''',
    }
    
    return PATTERNS.get(pattern_name)

