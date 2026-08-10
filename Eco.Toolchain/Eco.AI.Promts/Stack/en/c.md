---
name: C Code Style and Guidelines
description: Global code generation rules, style guide, and C development standards in the Eco model
version: 1.1.0
---

# TECHNICAL STACK: C LANGUAGE (ECO STANDARDS)

This document defines the code style and formatting guidelines for all subsequent files (`.c`, `.h`) generated within this assembly recipe.

## 1. FILE FORMATTING STANDARDS
- **Character Encoding**: All header and implementation files must be strictly generated using **UTF-8 with signature (BOM) / Codepage 65001**.
- **File Headers**: Every created file must begin with the following comment block:
  ```cpp
  /*
   * <character encoding> Cyrillic (UTF-8 with signature) - Codepage 65001 </character encoding>
   * <summary> [Brief summary of the file's purpose] </summary>
   * <description> [Detailed description of the business logic or structure] </description>
   * <reference> </reference>
   * <author> Copyright (c) 2026 [AUTHOR]. All rights reserved. </author>
   */
  ```

## 2. FUNCTION AND METHOD STANDARDS
- **Method Documentation**: Every function and virtual table (VTbl) method must include a header:
  ```cpp
  /*
   * <summary> [Function purpose] </summary>
   * <description> [Algorithm details, parameter breakdown, and return codes] </description>
   */
  ```
- **Pointer Validation**: Every interface method must explicitly validate incoming pointers against `NULL` at the very beginning:
  ```cpp
  if (me == NULL || ppv == NULL) {
      return ERR_ECO_POINTER;
  }
  ```

## 3. MEMORY AND DATA TYPE DISCIPLINE
- **No Standard C Types**: Using primitive types like `int`, `char`, `long`, `void*` is strictly forbidden. Use Eco-specific types instead: `int16_t`, `char_t`, `byte_t`, `voidptr_t`.
- **Memory Management**: Direct calls to `malloc`, `calloc`, or `free` are forbidden. Memory allocation must strictly use the component's internal allocator:
  ```cpp
  pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, size);
  ```

## 4. TEMPLATE AND MACRO PROCESSING
- When processing individual template files (from the `assembly` section), the AI must strictly preserve their syntax, substituting brackets-wrapped macros (`[PROJECT_NAME]`, `[GUID_CID_FORMATED]`, etc.) with real project metadata according to **ACOM** logic.

## 5. TEMPLATE INTEGRATION AND FALLBACK
- **Assembly Sequence**: Specific file templates are attached directly below in the system prompt assembly via the `assembly` recipe.
- **Interpretation Rule**: The AI must strictly apply the encoding, header formatting, and data type disciplines from sections 1–3 of this document (`c.md`) to **all subsequent file templates** listed below. Each subsequent code file will be wrapped in a markdown code block with its original filename specified in the comments.
- **Fallback Rule**: If specific template files are not explicitly appended below in the prompt text, the AI (acting as a coder) must fetch and use the standard reference blueprints from the system **`Templates/`** directory, choosing the subfolder based on the target file extension:
  - For **C** (`*.c`, `*.h`): `Templates/C/` folder (files like `IdROOT.h`, `CROOT.h`, `CROOT.c`, etc.).
