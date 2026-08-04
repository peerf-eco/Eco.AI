# Сборка и подключение RAG-хранилища (production-путь V7)

> Canonical operational documentation is maintained in
> `WORKING_DOCUMENTATION.md`; this file is retained for compatibility.

> Этот документ описывает **боевой** RAG: `marketplace_cache/` → `marketplace_index.sqlite`
> (sqlite-vec + FTS5) → EcoTool `search_marketplace`, который вызывают агенты architect и
> coder в пайплайне `/ws/v7/chat`.
>
> Старый путь на ChromaDB (`init_rag.py` / `rag_storage/` / `chroma_db/`) **снят** в ходе
> очистки 2026-06-22 — см. историческую справку в конце.

## 0. Что строим (TL;DR)

```
marketplace_cache/<Component>/SharedFiles/*.h   (корпус, ~30 МБ, 175 .h, 30 компонентов)
        │  scripts/fetch_marketplace.py  (eco-cli pull)
        ▼
scripts/build_marketplace_index.py
   ├─ ASTChunker(target_chars=400)        agent/rag/chunker_ast.py
   ├─ Embedder(qwen/qwen3-embedding-8b)    agent/rag/embedder.py  → OpenRouter /embeddings, 4096-dim
   └─ RagStore (sqlite-vec vec0 + FTS5)    agent/rag/store.py
        ▼
marketplace_index.sqlite  (в корне проекта; 1217 чанков; ~34 МБ)
        │  docker-compose mount :ro → /app/marketplace_index.sqlite
        ▼
EcoTool search_marketplace  (agent/v6/tools/rag.py)  ← вызывают architect и coder
```

Текущий индекс на диске (проверено чтением meta-таблицы): **1217 чанков, 30 компонентов,
175 файлов, model=qwen/qwen3-embedding-8b, dim=4096, chunker=ast**.

## 1. Предусловия

1. **Python-зависимости** (`agent/requirements.txt`):
   - `sqlite-vec>=0.1.6` — расширение SQLite для ANN (грузится в рантайме в `RagStore`, `store.py`).
   - `tree-sitter>=0.23,<0.24` и `tree-sitter-c==0.21.4` — AST-чанкер. **Пин обязателен**:
     tree-sitter-c 0.23 эмитит ABI v15, который tree-sitter 0.23.x не грузит; 0.21.4 даёт
     ABI v14 (`requirements.txt:94-100`).
   - `httpx>=0.27` — клиент к OpenRouter (`agent/rag/embedder.py`).
   ```bash
   pip install -r agent/requirements.txt
   ```

2. **Переменные окружения** (в `.env`, шаблон — `env.example`):
   - `OPENAI_API_KEY` — ключ OpenRouter (`sk-or-v1-...`). Читается `Embedder` как `OPENAI_API_KEY`,
     затем `OPENROUTER_API_KEY`. Без него embed падает с `EmbedderError`.
   - `OPENROUTER_URL` — по умолчанию `https://openrouter.ai/api/v1`.
   - `EMBEDDINGS_MODEL` — по умолчанию `qwen/qwen3-embedding-8b`. **Модель должна совпадать с
     той, на которой строился индекс** — иначе размерность вектора не сойдётся (dim проверяется
     при первом запросе).
   - `MARKETPLACE_INDEX_PATH` (необязательно) — путь к индексу для рантайма. Дефолт
     `/app/marketplace_index.sqlite` (контейнер) (`agent/v6/tools/rag.py:47-50`).
   - `ECO_API_TOKEN` — токен маркетплейса, нужен только для шага 2 (скачивание корпуса).

3. **eco-cli** — нужен только для шага 2. Путь через `ECO_CLI_BIN`, дефолт
   `eco.sli/eco-cli.exe` в корне репозитория (`scripts/fetch_marketplace.py`).

## 2. Подготовить корпус (`marketplace_cache/`)

> `marketplace_cache/` в `.gitignore` — в репозитории его нет, нужно собрать локально. Если
> каталог уже есть (30 компонентов на диске) — шаг можно пропустить, скрипт идемпотентен.

```bash
export ECO_API_TOKEN=<ваш токен маркетплейса>
# по умолчанию пишет в .../Eco.AI.Assembly1/marketplace_cache
python scripts/fetch_marketplace.py
```

Что делает `scripts/fetch_marketplace.py`:
- идёт по жёстко зашитому списку из 30 компонентов;
- для каждого: `eco find -p -n <Name>` → берёт последний DEVKIT → `eco pull -c <uguid>
  -v <ver> -fid=<fileId>` в `marketplace_cache/`;
- уже скачанные пропускает;
- итог пишет в `marketplace_cache/_fetch_summary.json`.

Раскладка на выходе: `marketplace_cache/<Component>/SharedFiles/*.h`. Ingest берёт только
`.h/.hpp/.c/.cpp/.inc/.ipp/.tpp`, каталоги `BuildFiles/` пропускает (`agent/rag/ingest.py`).

## 3. Построить индекс (`marketplace_index.sqlite`)

```bash
# Первый раз ИЛИ после докачки новых компонентов:
python scripts/build_marketplace_index.py

# Принудительно перестроить (стереть + переэмбеддить):
python scripts/build_marketplace_index.py --rebuild

# (опционально) другой размер чанка; дефолт 400 — победитель эвала:
python scripts/build_marketplace_index.py --rebuild --target-chars 400
```

Аргументы (из argparse, `scripts/build_marketplace_index.py`):
- `--rebuild` — перестроить, даже если индекс существует. Без него и при наличии файла скрипт
  ничего не делает и выходит с кодом 0.
- `--target-chars` (int, дефолт `400`) — размер чанка ASTChunker в non-whitespace символах.

Что под капотом:
1. `Embedder()` + warmup-embed — узнать размерность (4096 для qwen3-embedding-8b).
2. `RagStore.create(marketplace_index.sqlite, embed_dim, reset=True)` — создать схему
   (таблицы `chunks`, `vec_chunks` vec0, `fts_chunks` fts5, `meta`).
3. `ASTChunker(target_chars=400)` (выбран как победитель 4-way eval, см. §6).
4. `ingest_cache(...)` — walk → chunk → batch-embed (32/запрос) → одна транзакция в store.

Выход — **`marketplace_index.sqlite` в корне проекта** (gitignored). Стоимость/время:
~1200 чанков ≈ $0.05, ~2 мин.

## 4. Куда попадают артефакты и как их монтирует docker-compose

- Индекс лежит в `Eco.AI.Assembly1/marketplace_index.sqlite` (gitignored).
- `docker-compose.yml` монтирует в контейнер `api` read-only:
  ```yaml
  - ./marketplace_index.sqlite:/app/marketplace_index.sqlite:ro
  - ./marketplace_cache:/app/marketplace_cache:ro
  ```
- Рантайм-инструмент читает путь из `MARKETPLACE_INDEX_PATH` (дефолт
  `/app/marketplace_index.sqlite`). На dev-хосте без env используется тот же дефолтный путь —
  поэтому индекс держим в корне.

## 5. Проверить индекс

Подсчёт чанков и метаданных прямо из sqlite:
```bash
python - <<'PY'
import sqlite3, json
c = sqlite3.connect("marketplace_index.sqlite")
print("chunks:", c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])               # ожид. 1217
print("components:", c.execute("SELECT COUNT(DISTINCT component) FROM chunks").fetchone()[0])  # 30
s = json.loads(c.execute("SELECT value FROM meta WHERE key='ingest_stats'").fetchone()[0])
print(s["embed_model"], s["embed_dim"], s["chunker"], s["files"])      # qwen/qwen3-embedding-8b 4096 ast 175
PY
```
Ожидаемо: `chunks: 1217`, `components: 30`, `qwen/qwen3-embedding-8b 4096 ast 175`.

Боевой запрос через сам инструмент (требует `OPENAI_API_KEY` — реально дёргает OpenRouter):
```bash
python - <<'PY'
from agent.v6.tools.rag import make_search_marketplace_tool
tool = make_search_marketplace_tool()          # путь из MARKETPLACE_INDEX_PATH
args = tool.args_schema(query="mathematical functions like pow and sqrt", k=5)
print(tool.execute(args).content)
PY
```
Ожидаемо: топ-результат — `Eco.Math.C89/SharedFiles/IEcoMathC89.h` с `kind=interface`.

Оффлайн-проверка контракта инструмента (без сети): `pytest agent/v6/tests/test_tool_rag.py`
(моки Embedder/Store/Retriever).

## 6. Как агент это потребляет (рантайм)

- `/ws/v7/chat` (`backend/server.py:1153`) строит Orchestrator из architect/coder/tester.
- `make_architect` (`agent/v6/agents/architect.py`) и `make_coder` (`agent/v6/agents/coder.py`)
  добавляют `make_search_marketplace_tool()` — EcoTool с именем `search_marketplace`.
- При вызове `search_marketplace(query, k, kind?, component?)`:
  1. lazy-init Embedder + RagStore + HybridRetriever, кэш в замыкании;
  2. `retriever.search_vector_only(...)` — **только вектор** (гибрид BM25+RRF намеренно
     отвергнут: деградирует Recall@5 на нашем корпусе);
  3. возвращает markdown топ-K `component/file:Lstart-Lend kind name score + сниппет`.
- Дальше агент тянет выбранный компонент через `eco_cli` — `search_marketplace` отвечает на
  «КАКОЙ», `eco_cli` «КАЧАЕТ».

Почему AST-чанкер (`experiments/chunking_eval/report.md`): из 4 стратегий `ast` лучший —
R@1=0.90, R@5=0.95, MRR=0.92; по категориям semantic/exact_name/error_code Recall@5=1.00.
Почему vector-only, а не hybrid+RRF: на нашем корпусе vector_only Recall@5=1.00 > hybrid_rrf
0.95 (Qwen3-embedding сам различает идентификаторы).

---

## Историческая справка: legacy ChromaDB-путь (СНЯТ 2026-06-22)

До очистки в репозитории сосуществовал второй, **мёртвый** RAG-стек на ChromaDB:
`rag_storage/` (корпус, дублировавший `source/`) → `scripts/init_rag.py` (langchain
`OpenAIEmbeddings` + `RecursiveCharacterTextSplitter` + `Chroma.from_documents`) → `chroma_db/`,
коллекция `ecoos_components`. Триггерился сервисом `init-rag` в docker-compose, эндпоинтом
`GET /api/init-rag` и кнопкой «Create Vector Store» в UI (`rag-initializer.tsx`).

**Почему сняли:** продакшн-агенты V7 этот индекс не читали — `chroma_db` использовался только
легаси-узлом V3 (`agent/nodes/retrieve.py`), а кнопка в проде-UI строила индекс, который никто
не запрашивал (вводила в заблуждение). Снято: `rag_storage/`, `scripts/init_rag.py`, сервис
`init-rag`, эндпоинты `/api/init-rag` + `/api/rag-status`, компонент `RagInitializer`,
зависимости `chromadb`/`langchain-chroma`/`langchain-community`/`langchain-text-splitters`.

> Легаси-узел V3 `agent/nodes/retrieve.py` оставлен на месте (он за legacy-эндпоинтом
> `/ws/chat`), но без `chroma_db` его `rag_query` теперь всегда возвращает «ChromaDB not
> initialized». Это ожидаемо: V3 — не продакшн.
