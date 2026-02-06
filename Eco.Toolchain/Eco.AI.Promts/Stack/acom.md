# ECO COMPONENT MODEL (ACOM)
- **Naming**: [PROJECT_NAME] в CamelCase, [UPPER_PROJECT_NAME] в UPPER_CASE. Если в имени не указано явно Eco^ то добавляй его к имени как префикс.
- **Directory Structure**: 
    AssemblyFiles, BuildFiles, DependenciesFiles, DesignFiles, HeaderFiles, SharedFiles, SourceFiles, UnitTestFiles.
- **File Mapping**:
    - IDL: `SharedFiles/Eco[Name].idl`
    - C-Interface: `SharedFiles/IEco[Name].h`
    - ID-Header: `SharedFiles/IdEco[Name].h` (CID/IID)
    - Implementation: `SourceFiles/CEco[Name].c`

# UGUID RULE :
- Формат: {0x01, Length, {Data}}. 
- Preamble: 0x01. Length: 32bit=0x04, 64bit=0x08, 128bit=0x10, 256bit=0x20 и т.д.
- Комментарий перед IID/CID обязателен: /* Имя IID = {GUID} */.

# ECO MACROS & NAMING CONVENTION
Используй следующие макросы при генерации кода и шаблонов:
- `[FIX_PROJECT_NAME]`: Имя проекта (CamelCase).
- `[UPPER_PROJECT_NAME]`: Имя проекта (UPPER_CASE).
- `[AUTHOR]`: Автор проекта.
- `[METHOD_NAME] / [METHOD_PARAMETERS]`: Сигнатуры методов интерфейса.
- `[GUID_CID] / [GUID_IID]`: Data поле UGUID применяй правила логики UGUID. Пример: {93221116-2248-4742-AE06-82819447843D}, {A1B2C3D4E5F60708}.
- `[GUID_CID_FORMATED] / [GUID_IID_FORMATED]`: Полный HEX-формат {0x01, Len, {Data}}. Пример: {0x01, 0x10,
{0x12,0x34,0x56,0x78,0x90,0xab,0xcd,0xef,0xfe,0xdc,0xba,0x09,0x87,0x65,0x43,0x21}};
- `[GUID_CID_NAMESPACE]`: Последние 4 цифры CID в HEX (напр. CEcoMath_9447843D).
- `[GUID_CID_TARGET]`: Форматированный CID после `GetIEcoComponentFactoryPtr_`. Пример: GetIEcoComponentFactoryPtr_9322111622484742AE0682819447843D

# TEMPLATE LOGIC
Всегда обрабатывай условные блоки в шаблонах:
- `[!if ADD_CONNECTION_POINTS]`: Для систем с обратными интерфейсами (Events).
- `[!if ADD_AGGREGATION_INNER/OUTER]`: Для логики агрегирования (COM-style).
- `[!if ADD_CONTAINMENT_OUTER]`: Для реализации включения (Containment).
