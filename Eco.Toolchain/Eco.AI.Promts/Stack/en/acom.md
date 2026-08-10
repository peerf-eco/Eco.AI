---
name: Eco Component Model (ACOM)
description: Naming standards, directory structure, macros, and UGUID rules for the Eco component model
version: 1.0.0
---

# ECO COMPONENT MODEL (ACOM)
- **Naming**: `[PROJECT_NAME]` in CamelCase, `[UPPER_PROJECT_NAME]` in UPPER_CASE. If the name does not explicitly start with the `Eco` prefix, add it automatically.
- **Directory Structure**: 
    AssemblyFiles, BuildFiles, DependenciesFiles, DesignFiles, HeaderFiles, SharedFiles, SourceFiles, UnitTestFiles.
- **File Mapping**:
    - IDL: `SharedFiles/Eco[Name].idl`
    - C-Interface: `SharedFiles/IEco[Name].h`
    - ID-Header: `SharedFiles/IdEco[Name].h` (CID/IID)
    - Implementation: `SourceFiles/CEco[Name].c`

# UGUID RULE
- Format: `{0x01, Length, {Data}}`. 
- Preamble: `0x01`. Length: 32bit=`0x04`, 64bit=`0x08`, 128bit=`0x10`, 256bit=`0x20` etc.
- A comment before the IID/CID is required: `/* Name IID = {GUID} */`.

# ECO MACROS & NAMING CONVENTION
Use the following macros when generating code and templates:
- `[FIX_PROJECT_NAME]`: Project name (CamelCase).
- `[UPPER_PROJECT_NAME]`: Project name (UPPER_CASE).
- `[AUTHOR]`: Project author.
- `[METHOD_NAME] / [METHOD_PARAMETERS]`: Interface method signatures.
- `[GUID_CID] / [GUID_IID]`: The Data field of the UGUID, applying UGUID logic rules. Example: `{93221116-2248-4742-AE06-82819447843D}`, `{A1B2C3D4E5F60708}`.
- `[GUID_CID_FORMATED] / [GUID_IID_FORMATED]`: Full HEX format `{0x01, Len, {Data}}`. Example: `{0x01, 0x10, {0x12,0x34,0x56,0x78,0x90,0xab,0xcd,0xef,0xfe,0xdc,0xba,0x09,0x87,0x65,0x43,0x21}}`;
- `[GUID_CID_NAMESPACE]`: The last 8 symbols of the CID in HEX (e.g., `CEcoMath_9447843D`).
- `[GUID_CID_TARGET]`: Formatted CID appended after `GetIEcoComponentFactoryPtr_`. Example: `GetIEcoComponentFactoryPtr_9322111622484742AE0682819447843D`

# TEMPLATE LOGIC
Always process conditional blocks in templates:
- `[!if ADD_CONNECTION_POINTS]`: For systems with reverse interfaces (Events).
- `[!if ADD_AGGREGATION_INNER/OUTER]`: For aggregation logic (COM-style).
- `[!if ADD_CONTAINMENT_OUTER]`: For containment implementation.
