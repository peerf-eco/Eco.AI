# Eco.GGUF1

Eco.GGUF1 - это Eco-компонент для чтения, валидации и записи файлов GGUF v3.
Реализация сохраняет metadata и tensor payload как непрозрачные данные на
уровне Eco API и при этом сохраняет исходную раскладку файла при round-trip
записи.

## Область применения

- имя компонента: `EcoGGUF1`
- публичный корневой интерфейс: `IEcoGGUF1`
- поддерживаемая версия GGUF: `3`
- выравнивание тензоров по умолчанию: `32`
- режим хранения tensor payload:
  - в памяти для небольших входных данных, загруженных из памяти;
  - file-backed streaming для `readFile()`, чтобы большие модели не копировались
    в `IEcoRawData1`.

## Публичные Eco-интерфейсы

Модуль определяет GGUF-специфичные Eco-интерфейсы в `SharedFiles`:

- `IEcoGGUF1`
- `IEcoGGUF1File`
- `IEcoGGUF1TensorInfo`
- `IEcoGGUF1MetadataKV`
- `IEcoGGUF1MetadataValue`
- `IEcoRawData1`

Реализации компонентов находятся в `SourceFiles`, а приватные заголовки
компонентов - в `HeaderFiles`.

## Необходимые заголовки Eco SDK

В репозитории есть GGUF-специфичные заголовки, но стандартные заголовки Eco
framework должны быть доступны через include path Eco SDK:

- `IEcoBase1.h`
- `IEcoSystem1.h`
- `IEcoInterfaceBus1.h`
- `IEcoList1.h`
- `IdEcoInterfaceBus1.h`
- `IdEcoList1.h`
- `IdEcoMemoryManager1.h`
- `IdEcoString1.h`
- `IdEcoFileSystemManagement1.h`

Для Eco unit test дополнительно нужны:

- `IdEcoLog1.h`
- `IEcoLog1FileAffiliate.h`

В build-проектах нужно добавить include-директорию Eco SDK перед компиляцией
файлов из `SourceFiles`, `HeaderFiles`, `SharedFiles` и `UnitTestFiles`.

## Структура исходников

- `SharedFiles/` - публичные GGUF Eco-интерфейсы, идентификаторы, определения и
  локальный заголовок GGUF C API.
- `HeaderFiles/` - приватные заголовки компонентов.
- `SourceFiles/` - реализация Eco-компонента и GGUF parser/writer.
- `DesignFiles/` - локальные design notes и справочные заметки по upstream GGUF.
- `AssemblyFiles/` - placeholder-директории сборки, соответствующие layout
  репозиториев Eco-компонентов.
- `UnitTestFiles/SourceFiles/` - точки входа для Eco-теста и standalone C-теста.
- `UnitTestFiles/TestFiles/` - локальная директория для sample-файлов. Большие
  модели `.gguf` и сгенерированные бинарники не должны попадать в commit.

## Валидация

Текущий GGUF reader/writer проверяет:

- magic и version GGUF;
- metadata и tensor descriptors;
- строки с префиксом длины, включая embedded NUL bytes;
- выравнивание tensor offset;
- границы tensor data, ожидаемые размеры в байтах и пересечения;
- защиту от перезаписи исходного файла при source-backed записи.

`writeFileToMemory()` намеренно ограничен контрактом Eco raw-data API, где
размер представлен как `uint32_t`. Для больших GGUF-моделей используйте
`writeFile()`.
