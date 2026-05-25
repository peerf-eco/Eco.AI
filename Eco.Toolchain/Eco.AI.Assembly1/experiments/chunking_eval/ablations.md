# Retrieval Ablations on AST Index

Generated: 2026-05-24 01:08:23
Index: `ast.sqlite` (1217 chunks)
Queries: 20 golden

## Aggregate (held: chunker=ast, embed=qwen3-8b, only retrieval varies)

| retrieval | R@1 | R@3 | R@5 | R@10 | MRR | CompR@5 |
|---|---|---|---|---|---|---|
| vector_only | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| bm25_only | 0.55 | 0.75 | 0.80 | 0.85 | 0.65 | 0.80 |
| hybrid_rrf | 0.90 | 0.95 | 0.95 | 0.95 | 0.92 | 0.95 |

## Per-category Recall@5

| retrieval | error_code | exact_name | semantic | type_layout |
|---|---|---|---|---|
| vector_only | 1.00 | 1.00 | 1.00 | 1.00 |
| bm25_only | 0.80 | 1.00 | 0.80 | 0.60 |
| hybrid_rrf | 1.00 | 1.00 | 1.00 | 0.80 |

## Per-query first-correct-rank (— = not in top-10)

| query | vector_only | bm25_only | hybrid_rrf |
|---|---|---|---|
| `sem-01` component for calculating power and square root of a nu | #1 | — | #1 |
| `sem-02` how do I register a component on the interface bus | #1 | #3 | #1 |
| `sem-03` manage threads and synchronize critical sections | #1 | #2 | #1 |
| `sem-04` read and write files on disk | #1 | #3 | #1 |
| `sem-05` standard I/O like printf and scanf | #1 | #1 | #1 |
| `exact-01` IEcoComponentFactory interface vtable layout with Query | #1 | #1 | #1 |
| `exact-02` IEcoSystem1 interface for getting subsystems | #1 | #1 | #1 |
| `exact-03` IEcoMemoryAllocator1 Allocate Free methods | #1 | #1 | #1 |
| `exact-04` IEcoList1 interface methods Insert Remove | #1 | #2 | #1 |
| `exact-05` IEcoInterfaceBus1 RegisterComponent | #1 | #1 | #1 |
| `err-01` ERR_ECO_NOBUS meaning | #1 | #1 | #1 |
| `err-02` ERR_ECO_NOAGGREGATION code 0xFFEA | #1 | #1 | #1 |
| `err-03` ECOCALLMETHOD calling convention macro | #1 | #1 | #1 |
| `err-04` ECO_EXPORT and ECOCALL function attribute macros | #1 | #4 | #1 |
| `err-05` CID_EcoMath1 component ID GUID literal | #1 | — | #3 |
| `type-01` UGUID struct fields Preamble Length Data | #1 | #1 | #1 |
| `type-02` IEcoUnknown vtable QueryInterface AddRef Release | #1 | #1 | #1 |
| `type-03` int16_t byte_t voidptr_t basic typedefs | #1 | #1 | #1 |
| `type-04` list iterator typedef IEcoListEnumerator | #1 | #9 | #1 |
| `type-05` vector data structure typedef | #1 | — | — |