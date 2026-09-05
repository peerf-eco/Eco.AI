---
name: Eco Component Model (ACOM)
description: Naming standards, directory structure, macros, and UGUID rules for the Eco component model
version: 1.0.0
---

# ECO COMPONENT MODEL (ACOM)
- **Naming**: `[PROJECT_NAME]` in CamelCase, `[UPPER_PROJECT_NAME]` in UPPER_CASE. If the name does not explicitly start with the `Eco` prefix, add it automatically as a prefix.

- **MANDATORY DEV-KIT & SYSTEM ENVIRONMENT (CRITICAL HIGHEST PRIORITY)**:
    - **Interface Resolution (Strict API Boundary)**: To include header files, the AI must locate existing interfaces exclusively inside the project's local `DependenciesFiles/` directory or via the path provided in the `ECO_FRAMEWORK` environment variable (hereinafter referred to as `<FRAMEWORK_PATH>`). The AI is allowed to use files **only** from the `SharedFiles` subfolders (e.g., `<FRAMEWORK_PATH>/<ComponentName>/SharedFiles/`), as they represent the official public API. Accessing or looking into `HeaderFiles` or `SourceFiles` of other (external) projects is **strictly forbidden** unless explicitly requested by the technical specification. 
    - **Mandatory Core (Eco.Core1)**: The files inside `<FRAMEWORK_PATH>/Eco.Core1/SharedFiles` are the mandatory base foundation of every project. They contain all core ACOM data types and macros that the AI must use instead of standard primitive C types.
    - **Minimum Required Stack**: When designing and building any new component or application logic, the AI must always assume and utilize the following baseline of system interfaces:
      - `Eco.InterfaceBus1` — the system interface bus for component discovery, querying, and registration.
      - `Eco.MemoryManager1` — the memory manager providing core allocation services.
      - `Eco.FileSystemManagement1` — the subsystem handling low-level file system operations.
    - **Entry Point (Eco.System1)**: The `Eco.System1` system library acts as the mandatory unified entry point (`EcoMain`) for compiling cross-platform unikernel applications.

- **Directory Structure**: 
    - Create the following folder structure in the root directory of the project if it does not exist:
      `AssemblyFiles`, `BuildFiles`, `DependenciesFiles`, `DesignFiles`, `HeaderFiles`, `SharedFiles`, `SourceFiles`, `UnitTestFiles`.
    - For cross-platform development, create a separate folder for each platform inside the `AssemblyFiles` directory if it does not exist:
      `Android`, `EcoOS`, `iOS`, `Linux`, `Mac`, `Windows`
    - For toolchains, create a folder corresponding to the toolchain name inside the respective `AssemblyFiles/<Platform>` directory if it does not exist: e.g., `gcc-riscv`, `VS_v100`, `MSVC_v140`, `Xcode_v123`.

- **File Mapping**:
    - Create or work with existing files according to the project structure:
    - IDL: `SharedFiles/Eco[Name].idl`
    - C-Interface: `SharedFiles/IEco[Name].h`
    - ID-Header: `SharedFiles/IdEco[Name].h` (CID/IID)
    - Object Implementation: `SourceFiles/CEco[Name].c`
    - Object Header: `HeaderFiles/CEco[Name].h`
    - Factory Implementation: `SourceFiles/CEco[Name]Factory.c`
    - Factory Header: `HeaderFiles/CEco[Name]Factory.h`
    - Add New Object Implementation: `SourceFiles/CEco[NewName].c`
    - Add New Object Header: `HeaderFiles/CEco[NewName].h`
    - Unit-Test Implementation: `UnitTestFiles/SourceFiles/Eco[Name].c`
    - Unit-Test Header (Optional): `UnitTestFiles/HeaderFiles/Eco[Name].h`
    - Component Makefile: `AssemblyFiles/<Platform>/<Toolchain>/Makefile`
    - Unit-Test Makefile: `AssemblyFiles/<Platform>/<Toolchain>/MakefileExe`
    - IDE Project Files: `AssemblyFiles/<Platform>/<Toolchain>/*`

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
- `[GUID_CID_NAMESPACE]`: Strictly the last 8 symbols of the CID in HEX (e.g., `CEcoMath_9447843D`).
- `[GUID_CID_TARGET]`: Formatted CID appended after `GetIEcoComponentFactoryPtr_`, strictly the entire CID. Example: `GetIEcoComponentFactoryPtr_9322111622484742AE0682819447843D`

# TEMPLATE LOGIC
Always process conditional blocks in templates:
- `[!if ADD_CONNECTION_POINTS]`: For systems with reverse interfaces (Events).
- `[!if ADD_AGGREGATION_INNER/OUTER]`: For aggregation logic (COM-style).
- `[!if ADD_CONTAINMENT_OUTER]`: For containment implementation.
