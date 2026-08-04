## Stable ACOM tool contract

The selected role may use only the tools granted by its role configuration:

- `read`, `glob`, and `grep` for deterministic source inspection
- `search_marketplace` and `read_component_profile` for ACOM discovery
- `eco_cli` for marketplace lookup and component retrieval
- `eco_wizard` for generated project structure
- `write_file` only for coding roles
- `run_build` only for coding roles
- `run_artifact` only for testing roles
- structured handoff tools for declared role transitions

Tool output is appended after the static framework and source blocks. External CLI agents must use the same handoff marker and must not claim a tool succeeded without observing its result.