---
name: Eco Component Model (ACOM)
description: Стандарты именования, структура директорий, макросы и правила UGUID для компонентной модели Eco
version: 1.0.0
---

# ECO COMPONENT MODEL (ACOM)
- **Naming**: `[PROJECT_NAME]` в CamelCase, `[UPPER_PROJECT_NAME]` в UPPER_CASE. Если в имени не указано явно префикса `Eco`, то автоматически добавляй его к имени как префикс.

- **ОБЯЗАТЕЛЬНОЕ СИСТЕМНОЕ ОКРУЖЕНИЕ И DEVKIT (ВЫСШИЙ ПРИОРИТЕТ)**:
    - **Поиск интерфейсов (Строгое ограничение API)**: Для включения заголовочных файлов ИИ обязан искать существующие интерфейсы исключительно в локальной папке проекта `DependenciesFiles/` или во внешней папке по пути из переменной окружения `ECO_FRAMEWORK` (далее обозначается как `<FRAMEWORK_PATH>`). Допускается использовать файлы **только** из подпапок `SharedFiles` (например, `<FRAMEWORK_PATH>/<ComponentName>/SharedFiles/`), так как они представляют собой публичное API. Заходить в папки `HeaderFiles` или `SourceFiles` других (чужих) проектов **категорически запрещено**, если об этом прямо и явно не попросили в техническом задании. 
    - **Обязательное ядро (Eco.Core1)**: Файлы из `<FRAMEWORK_PATH>/Eco.Core1/SharedFiles` являются базовым фундаментом проекта. Они содержат типы данных и макросы ACOM, которые ИИ обязан использовать взамен стандартных типов C.
    - **Базовые интерфейсы**: При проектировании любой логики ИИ должен использовать системную шину `Eco.InterfaceBus1` для получения фабрик, менеджер памяти `Eco.MemoryManager1` для аллокации ресурсов и `Eco.FileSystemManagement1` для работы с файлами.
    - **Точка входа**: Для сборки кроссплатформенных unikernel-приложений всегда генерируй функцию `EcoMain`, опираясь на системную библиотеку `Eco.System1`.

- **Directory Structure**: 
    - Создавай следующую структуру папок в корневой папке проекта, если она не создана:
      `AssemblyFiles`, `BuildFiles`, `DependenciesFiles`, `DesignFiles`, `HeaderFiles`, `SharedFiles`, `SourceFiles`, `UnitTestFiles`.
    - Для кроссплатформенной разработки в папке `AssemblyFiles` создавай для каждой платформы свою папку, если она не создана:
      `Android`, `EcoOS`, `iOS`, `Linux`, `Mac`, `Windows`
    - Для toolchain в соответствующей папке `AssemblyFiles/<Platform>` создавай свою папку, соответствующую имени набора инструментов, если она не создана: к примеру `gcc-riscv`, `VS_v100`, `MSVC_v140`, `Xcode_v123`.

- **File Mapping**:
    - Создавай или работай с существующими файлами согласно структуре проекта:
    - IDL: `SharedFiles/Eco[Name].idl`
    - C-Interface: `SharedFiles/IEco[Name].h`
    - ID-Header: `SharedFiles/IdEco[Name].h` (CID/IID)
    - Object Implementation: `SourceFiles/CEco[Name].c`
    - Object Header: `HeaderFiles/CEco[Name].h`
    - Factory Implementation: `SourceFiles/CEco[Name]Factory.c`
    - Factory Header: `HeaderFiles/CEco[Name]Factory.h`
    - Add New Object Implementation: `SourceFiles/CEco[NewName].c`
    - Add New Object Header: `HeaderFiles/CEco[NewName].h`
    - Unit-Test Implementation: `UnitTestFiles/SourceFiles/Eco[Name].c`
    - Unit-Test Header (Optional): `UnitTestFiles/HeaderFiles/Eco[Name].h`
    - Component Makefile: `AssemblyFiles/<Platform>/<Toolchain>/Makefile`
    - Unit-Test Makefile: `AssemblyFiles/<Platform>/<Toolchain>/MakefileExe`
    - IDE Project Files: `AssemblyFiles/<Platform>/<Toolchain>/*`

# UGUID RULE
- Формат: `{0x01, Length, {Data}}`. 
- Preamble: `0x01`. Length: 32bit=`0x04`, 64bit=`0x08`, 128bit=`0x10`, 256bit=`0x20` и т.д.
- Комментарий перед IID/CID обязателен: `/* Имя IID = {GUID} */`.

# ECO MACROS & NAMING CONVENTION
Используй следующие макросы при генерации кода и шаблонов:
- `[FIX_PROJECT_NAME]`: Имя проекта (CamelCase).
- `[UPPER_PROJECT_NAME]`: Имя проекта (UPPER_CASE).
- `[AUTHOR]`: Автор проекта.
- `[METHOD_NAME] / [METHOD_PARAMETERS]`: Сигнатуры методов интерфейса.
- `[GUID_CID] / [GUID_IID]`: Поле Data для UGUID, применяй правила логики UGUID. Пример: `{93221116-2248-4742-AE06-82819447843D}`, `{A1B2C3D4E5F60708}`.
- `[GUID_CID_FORMATED] / [GUID_IID_FORMATED]`: Полный HEX-формат `{0x01, Len, {Data}}`. Пример: `{0x01, 0x10, {0x12,0x34,0x56,0x78,0x90,0xab,0xcd,0xef,0xfe,0xdc,0xba,0x09,0x87,0x65,0x43,0x21}}`;
- `[GUID_CID_NAMESPACE]`: Строго последние 8 символов CID в HEX (напр. `CEcoMath_9447843D`).
- `[GUID_CID_TARGET]`: Форматированный CID после `GetIEcoComponentFactoryPtr_`, строго весь CID. Пример: `GetIEcoComponentFactoryPtr_9322111622484742AE0682819447843D`

# TEMPLATE LOGIC
Всегда обрабатывай условные блоки в шаблонах:
- `[!if ADD_CONNECTION_POINTS]`: Для систем с обратными интерфейсами (Events).
- `[!if ADD_AGGREGATION_INNER/OUTER]`: Для логики агрегирования (COM-style).
- `[!if ADD_CONTAINMENT_OUTER]`: Для реализации включения (Containment).
