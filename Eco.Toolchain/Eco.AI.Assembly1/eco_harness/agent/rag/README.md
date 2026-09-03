# agent/rag — Marketplace RAG Index

This package builds and queries a **hybrid vector + BM25 index** over the
EcoOS Marketplace component corpus. It powers the `search_marketplace`
EcoTool: an agent discovers a component by semantic/keyword search, then
pulls its DEVKIT via the marketplace CLI.

## Module layout

| File | Responsibility |
|------|----------------|
| `chunker_base.py` | `Chunk` dataclass + `Chunker` protocol |
| `chunker_ast.py` | `ASTChunker` — production chunker (target_chars=400) |
| `chunker_naive.py` | Flat fixed-size chunker (eval baseline) |
| `chunker_recursive.py` | Recursive character splitter (eval baseline) |
| `embedder.py` | `Embedder` — Qwen3-Embedding-8B via OpenRouter |
| `store.py` | `RagStore` — sqlite-vec (vectors) + FTS5 (BM25) in one `.sqlite` |
| `ingest.py` | `ingest_cache()` — walk → chunk → embed → store pipeline |
| `retrieve.py` | Query path: vector + BM25 fusion over the store |

## Build pipeline

`scripts/build_marketplace_index.py` drives `ingest_cache()`:

1. **Resolve embed dim** — probe the embedder once (`embed_one("warmup")`)
   because the `vec0` virtual-table schema bakes in the dimension.
2. **Create store** — `RagStore.create(INDEX_PATH, embed_dim=..., reset=True)`
   wipes any prior index.
3. **Ingest** — `ingest_cache(CACHE_DIR, store, ASTChunker(400), embedder)`:
   walk the cache, chunk every selected file, batch-embed, single
   transaction.
4. **Output** — `marketplace_index.sqlite` at the project root, mounted
   read-only into the docker-compose `api` service as
   `/app/marketplace_index.sqlite:ro`.

Re-run with `--rebuild` to wipe + re-embed. `--target-chars` overrides the
chunk size (default 400, the winner of the 4-way chunking eval).

## What gets indexed (corpus selection)

`ingest_cache` → `_iter_source_files` (ingest.py:39) decides what is
indexed. Selection rules:

- Only **directories** directly under `marketplace_cache/` are treated as
  components; top-level files are ignored.
- Directories whose name starts with `.` or `_` are skipped
  (`ingest.py:51`) — this excludes `.eco/` and `_profiles/`.
- Within a component, files are matched by extension against `_C_EXTS`
  (`ingest.py:33`):
  ```
  .h .hpp .c .cpp .inc .ipp .tpp .md .markdown .txt
  ```
  The actual `rglob` + suffix filter is at `ingest.py:54-58`:
  `for path in component_dir.rglob("*")` … `if path.suffix.lower() not in _C_EXTS: continue`.
- Files under any `BuildFiles/` path are skipped (`ingest.py:60`) — binary
  build outputs.
- Files are read with `utf-8-sig → utf-8 → cp1251 → latin-1`; anything that
  fails all decoders is recorded in `skipped` and dropped
  (`ingest.py:65`).

### Effective result

| Path | Indexed? | Reason |
|------|----------|--------|
| `marketplace_cache/<Component>/SharedFiles/*.h` | ✅ | The DEVKIT headers — main payload |
| `marketplace_cache/<Component>/DesignFiles/*` | ✅ only if ext in `_C_EXTS` | e.g. `.h/.md/.txt` |
| `marketplace_cache/<Component>/BuildFiles/*` | ❌ | Explicitly skipped |
| `marketplace_cache/<Component>/…` (`.lib/.so/.dll/.json`) | ❌ | Extension not allowed |
| `marketplace_cache/<Component>/_profiles/*.json` | ❌ | Dir starts with `_` |
| `marketplace_cache/.eco/` | ❌ | Dir starts with `.` |
| `marketplace_cache/ecoPackage.json` | ❌ | Top-level file + `.json` |
| `marketplace_cache/_fetch_summary.json` | ❌ | Top-level file + `_` prefix |

So the corpus is the **source/text files of each component's `SharedFiles/`
(and any `DesignFiles/` matching an allowed extension)** — roughly ~175 `.h`
files across the 31 components.

## `_profiles/` — content and role

`scripts/fetch_marketplace.py` writes `marketplace_cache/_profiles/<Name>.json`
for every component: the **raw `eco-cli find -n <Name>` profile** (marketplace
metadata: `uguid`, `versions[]`, per-version `files[]` with `contentType` /
`fileId`, etc.), captured at fetch time and saved with
`json.dumps(..., ensure_ascii=False)` (`fetch_marketplace.py:188`).

**It is intentionally NOT indexed** by the RAG pipeline (it lives in a `_`
-prefixed dir that `_iter_source_files` skips). Instead it serves a different
purpose:

- `agent/internal/tools/profile_cache.py` (`read_component_profile`) reads
  `marketplace_cache/_profiles/<Name>.json` to give an agent the
  `(cid, version, fileId)` tuple it needs to `pull` a DEVKIT — without
  spawning `eco-cli` or the full marketplace catalog dump
  (`profile_cache.py:17`).
- It is mounted read-only into production at `/app/marketplace_cache`
  (docker-compose ~line 27), and the tool resolves it via a fixed root so
  the architect's sandboxed `read_file` cannot reach it directly
  (`profile_cache.py:47`).
- If a profile is missing, the tool returns `is_error=True` and points the
  agent at the `eco-cli find -p` fallback (`profile_cache.py:86`).
- `code_search.py:261` also references `**/_profiles/*.json` as part of its
  searchable glob set.

In short: **the RAG index answers "which component matches my intent?"**,
while **`_profiles/` answers "given that component name, what do I pull?"** —
two complementary lookups in the same cache tree.

## Troubleshooting

- *"index exists" but the directory is empty / `IsADirectoryError`* — a stale
  `marketplace_index.sqlite` **directory** (often root-owned from the
  docker `api` service) is being mistaken for the index file. `RagStore.create`
  now `rmtree`s a directory path on `reset`; the build script also warns and
  removes non-file paths before rebuilding. Fix ownership with
  `sudo chown -R nick:nick marketplace_cache` if root keeps re-creating paths.
- *"cache is empty — nothing to index"* — run `scripts/fetch_marketplace.py`
  first (requires `ECO_API_TOKEN`).
