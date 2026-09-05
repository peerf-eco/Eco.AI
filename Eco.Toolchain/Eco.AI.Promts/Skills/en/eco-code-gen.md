---
name: Eco Project Generation Skills
description: Skills and scenarios for generating source code and components within the Eco model
version: 1.0.0
---

# SKILL: ECO PROJECT GENERATION
When creating a component project, strictly follow this order:
1. **IDL First**: Always start by describing interfaces in `.idl`.
2. **Factory Single**: Create exactly one factory (`CEco...Factory`) that implements `IEcoComponentFactory`.
3. **Multi-Interface**: A single component can implement N interfaces via one or multiple VTbls.
4. **Default**: Create a "Stand-alone" component by default.

# SKILL: ECO GENERATION SCENARIOS
Execute actions based on the following keywords in the request:
- **"Interface"**: Generate a VTbl structure or an abstract class.
- **"ID/CID/IID"**: Generate only a block of static UGUIDs.
- **"Application" (EcoMain)**: Full lifecycle: System -> Bus -> Component -> Release.
- **"Test"**: Generate EcoMain with method result validation (do not use assert).
