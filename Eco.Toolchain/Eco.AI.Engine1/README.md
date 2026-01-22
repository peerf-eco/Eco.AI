# Project Structure

This document describes the organization of folders and files within the project repository.

## Overview

The project is organized using a strict folder naming convention, where each folder contains files of a specific type and purpose. All folder names use `PascalCase` styling and end with the `Files` suffix.

```
/
├── AssemblyFiles
├── BuildFiles
├── DependenciesFiles
├── DesignFiles
├── HeaderFiles
├── SharedFiles
├── SourceFiles
└── UnitTestFiles
```

---

## Folder Descriptions

### `AssemblyFiles`

Contains scripts, configuration files, and tools necessary for the project's build process (e.g., `Makefile`, `pom.xml`, files for CI/CD, or automation scripts).

### `BuildFiles`

Contains the compiled output files of the project (executables, DLL libraries, `.jar` files, or other build artifacts), ready for deployment or execution.

### `DependenciesFiles`

Contains third-party libraries, frameworks, and external dependencies of the project that are not part of the core source code. These can be compiled libraries or source files of external packages.

### `DesignFiles`

Contains all artifacts related to the design and planning of the project: technical specifications (TS), UML diagrams, user interface mockups (UI/UX), database schemas, and other project documentation.

### `HeaderFiles`

Contains **private** header files (`.h`, `.hpp`) that describe the internal class structures and implementation details of the ACOM/COM components. These files are not intended for public consumption by external clients.

### `SharedFiles`

Contains **public** shared ACOM/COM interface header files (`.h`, `.hpp`) and Interface Definition Language source files (`.idl` files). These files provide external clients with the necessary information to interact with your component.

### `SourceFiles`

The core folder of the project. Contains the **main source code** of the application (`.c`, `.cpp`, `.py`, `.js`, `.java`, etc.).

### `UnitTestFiles`

Contains unit test files, integration tests, and other scripts for automated testing of the code located within `SourceFiles`.
