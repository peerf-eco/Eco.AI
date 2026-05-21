<<<<<<< HEAD
# AI проекты 
```
Eco.AI.git/
├── Eco.Toolchain/                                      # Набор инструментов
│ ├── Eco.AI.Assembly1/                                 # Сборочное программирование
│ ├── Eco.AI.ClearSet1/                                 # Проект де-дупликации данных 
│ ├── Eco.AI.DatasetGen1/                               # Проект генерации данных
│ ├── Eco.AI.DocsGen1/                                  # Проект генерации документов
│ ├── Eco.AI.Engine1/                                   # ПО для инференса моделей 
│ ├── Eco.AI.Inference1/                                # ПО для инференса моделей 
│ ├── Eco.AI.Promts/                                    # Системные промты 
│ ├── Eco.AI.Trainer1/                                  # Проект для подготовки данных и обучения моделей
│ ├── Eco.GGUF1/                                        # Формат файла LLM
│ ├── Eco.HDF5/                                         # Формат файла BigData/Container/LLM
│ ├── Eco.ONNX1/                                        # Формат файла LLM
│ └── Eco.RAG.ChatBot1/                                 # RAG-ассистент по компонентам Eco платформы
├── Eco.Shell/                                          # Интеллектуальная оболочка управления (Smart Shell)
└── README.md                                           # Этот файл
```
=======
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
>>>>>>> c711e5f4e3a6356e88022fc42210e0310781feee
