---
name: C Code Style and Guidelines
description: Global code generation rules, style guide, and C development standards in the Eco model
version: 1.1.0
---

# TECHNICAL STACK: C LANGUAGE (ECO STANDARDS)

This document defines the code style and formatting guidelines for all subsequent files (`.c`, `.h`) generated within this assembly recipe.

## 1. CODE STYLE AND COMPILATION STANDARDS
- **Language Standard**: All C code must strictly comply with the **C89 (ANSI C) - ANSI X3.159-1989** specification. Post-C89 features (such as mid-block variable declarations, `//` comments, or `stdbool.h`) are strictly forbidden. All variables must be declared at the very beginning of the block.
- **Safety Standards**: Code must adhere to **MISRA C** (Motor Industry Software Reliability Association) guidelines to ensure high reliability. Depending on the specification, follow:
  - MISRA C:1998 (First edition, 127 rules).
- **Character Encoding**: All header and implementation files must be strictly generated using **UTF-8 with signature (BOM) / Codepage 65001**.
- **Structure Alignment (`#pragma pack`)**: The `#pragma pack` directive must be used **only** for data structures that are serialized (saved) to files, transmitted over the network, or bound to strict binary standards where byte-perfect mapping is critical. For standard internal structures and component implementation objects, using `#pragma pack` is **forbidden** to preserve natural CPU alignment and prevent performance degradation.
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
- **No Standard C Types**: Using primitive types like `int`, `char`, `long`, `void*` is strictly forbidden. Use Eco-specific types instead: `int16_t`, `char_t`, `byte_t`, `voidptr_t`. All these types must be resolved from the mandatory core component `Eco.Core1/SharedFiles` (see DevKit lookups in ACOM).
- **Memory Management**: Direct calls to `malloc`, `calloc`, or `free` are forbidden. Memory allocation must strictly use the component's internal allocator interface `IEcoMemoryAllocator1` (provided by the `Eco.MemoryManager1` subsystem), accessed via the `m_pIMem` field:
  ```cpp
  pCMe->m_pIMem->pVTbl->Alloc(pCMe->m_pIMem, size);
  ```

## 4. TEMPLATE AND MACRO PROCESSING RULES
- **Template Location**: If specific code templates are not provided in the prompt text, the AI (acting as a coder) must fetch baseline blueprints from the **`Templates/`** folder located in the repository root or current directory.
  - For **C** (`*.c`, `*.h`): use `IdROOT.h`, `CROOT.h`, `CROOT.c`, etc., from the `Templates/` directory.
- **Macro Substitution**: When processing a template file, the AI must strictly preserve its syntax and substitute all brackets-wrapped placeholders (e.g., `[PROJECT_NAME]`, `[GUID_CID_FORMATED]`, `[AUTHOR]`) with real project metadata according to **ACOM** logic.
- **MANDATORY STEP-BY-STEP GENERATION ALGORITHM (STRUCTURE & HEADERS)**:
  The AI is **strictly forbidden** from dumping all files into a single root folder or generating undocumented code. Project generation must follow these exact steps:
  1. **Step 1: Directory Tree**: First, output the textual directory tree of the future project according to the **ACOM** spec (including `AssemblyFiles`, `HeaderFiles`, `SharedFiles`, `SourceFiles`, and platform subfolders).
  2. **Step 2: File Path**: Before generating each individual file, explicitly write its full relative destination path in bold text. *Example:* `File: SourceFiles/CEcoMath.c`.
  3. **Step 3: Mandatory File Header**: Every single markdown code block must begin with the standard `File Header` comment block from Section 1 (specifying the author, UTF-8 BOM encoding, and file description). Code blocks without this header are considered invalid.
  4. **Step 4: Function Documentation**: All functions, virtual table (VTbl) methods, and critical internal algorithms within the file must include the `Function Header` comment from Section 2.
- **Applying Style Guides**: All encoding guidelines, file/function header formats, C89/MISRA standards, memory disciplines, and structure alignment rules from sections 1–3 of this document **must be strictly applied** to all files generated from these templates.
