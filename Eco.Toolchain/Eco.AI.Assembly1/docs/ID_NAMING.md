# ID Naming Convention

The harness uses three distinct id namespaces. This document is the single
reference for "what prefix means what" — pointed to from the architect
prompt, `backend/session_export.py`, `backend/server.py:_project_entry`,
and the project panel.

| Prefix | Namespace | Example | Lives at | Scope |
|--------|-----------|---------|----------|-------|
| `proj-` | Project (card ref + display name for harness-generated dirs) | `proj-7K3F` | `output/proj-<8hex>/` | One build target folder; hosts many sessions |
| `ses-` | Session (id + trace dir) | `ses-1ca5b8f4` | `traces/ses-<8hex>/` | One chat thread / pipeline run; 1:1 with its trace dir |
| devkit id | Marketplace component | `Eco.MathC89` | `marketplace_cache/…` | One published component (versioned) |

## Rules

1. **Projects** (`proj-`): the default project dir is
   `output/proj-<8hex-of-thread>` (`server.py:_default_project_dir`). The
   panel card ref for harness-generated dirs is `proj-` + 4 base32 chars
   derived from the SHA-1 of the path (`_harness_project_ref`), stable
   across re-adds. User-registered folders keep the directory basename and
   a SHA-1-based id — `proj-` is never applied to them.
2. **Sessions** (`ses-`): the id is the first 8 hex chars of the thread
   UUID; the trace dir is `traces/ses-<id8>/`. Legacy `traces/chat-<id8>/`
   and `output/chat-<8hex>/` dirs remain discoverable
   (`_session_trace_dirs`, `_remap_to_output_root`).
3. **No new prefixes** without updating this file and the reference sites
   listed above. When adding a prefix, state: what it names, where it
   lives on disk, its scope (1:1 or 1:N), and how it is derived.
