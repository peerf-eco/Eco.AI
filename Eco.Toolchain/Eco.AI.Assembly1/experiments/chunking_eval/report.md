# Chunking Strategy Evaluation

Source: `experiments/chunking_eval/run_eval.py`

Generated: 2026-05-24 01:07:43

## Aggregate metrics

| chunker | R@1 | R@3 | R@5 | R@10 | MRR | CompR@5 | #chunks | #files | ingest_s |
|---|---|---|---|---|---|---|---|---|---|
| naive | 0.85 | 0.90 | 0.90 | 0.90 | 0.87 | 0.90 | 1112 | 175 | 106 |
| naive_overlap | 0.80 | 0.90 | 0.90 | 0.95 | 0.86 | 0.90 | 1312 | 175 | 122 |
| recursive | 0.85 | 0.85 | 0.85 | 0.95 | 0.86 | 0.90 | 1264 | 175 | 107 |
| ast | 0.90 | 0.95 | 0.95 | 0.95 | 0.92 | 0.95 | 1217 | 175 | 97 |

## Per-category Recall@5

| chunker | error_code | exact_name | semantic | type_layout |
|---|---|---|---|---|
| naive | 0.80 | 1.00 | 1.00 | 0.80 |
| naive_overlap | 0.80 | 1.00 | 1.00 | 0.80 |
| recursive | 0.80 | 1.00 | 0.80 | 0.80 |
| ast | 1.00 | 1.00 | 1.00 | 0.80 |

## Per-query top-5 results

Format: each query × each chunker → top-5 with hit marker (`✓`/`·`).

| query | naive | naive_overlap | recursive | ast |
|---|---|---|---|---|
| `sem-01` component for calculating power and square root of a number | #1 | #1 | #1 | #1 |
| `sem-02` how do I register a component on the interface bus | #3 | #1 | #6 | #1 |
| `sem-03` manage threads and synchronize critical sections | #1 | #2 | #1 | #1 |
| `sem-04` read and write files on disk | #1 | #1 | #1 | #1 |
| `sem-05` standard I/O like printf and scanf | #1 | #1 | #1 | #1 |
| `exact-01` IEcoComponentFactory interface vtable layout with QueryInter | #1 | #1 | #1 | #1 |
| `exact-02` IEcoSystem1 interface for getting subsystems | #1 | #1 | #1 | #1 |
| `exact-03` IEcoMemoryAllocator1 Allocate Free methods | #1 | #1 | #1 | #1 |
| `exact-04` IEcoList1 interface methods Insert Remove | #1 | #1 | #1 | #1 |
| `exact-05` IEcoInterfaceBus1 RegisterComponent | #1 | #1 | #1 | #1 |
| `err-01` ERR_ECO_NOBUS meaning | #1 | #1 | #1 | #1 |
| `err-02` ERR_ECO_NOAGGREGATION code 0xFFEA | #1 | #1 | #1 | #1 |
| `err-03` ECOCALLMETHOD calling convention macro | #1 | #1 | #1 | #1 |
| `err-04` ECO_EXPORT and ECOCALL function attribute macros | #1 | #2 | #1 | #1 |
| `err-05` CID_EcoMath1 component ID GUID literal | — | #7 | #10 | #3 |
| `type-01` UGUID struct fields Preamble Length Data | #1 | #1 | #1 | #1 |
| `type-02` IEcoUnknown vtable QueryInterface AddRef Release | #1 | #1 | #1 | #1 |
| `type-03` int16_t byte_t voidptr_t basic typedefs | #1 | #1 | #1 | #1 |
| `type-04` list iterator typedef IEcoListEnumerator | #1 | #1 | #1 | #1 |
| `type-05` vector data structure typedef | — | — | — | — |