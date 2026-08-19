# Workspace agent rules

The active production path is the ACOM meta-harness. Keep domain rules in `config/prompts/`, reusable skills in `config/skills/`, and role-specific rules in `config/agents/<role>/AGENTS.md` or `.eco-harness/agents/<role>/AGENTS.md`.

Use `eco-wizard` to generate templates for new ACOM component or application project structure and `eco-cli` to find and download the missing marketplace components. Do not put secrets in repository configuration.