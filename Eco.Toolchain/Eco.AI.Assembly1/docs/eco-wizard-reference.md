# Eco Wizard CLI - Quick Reference

## Build CLI

```cmd
cd packages\cli-app
bun run build
```
Output: `dist\eco-wizard.exe` (standalone, ~50MB)

## Basic Usage

```cmd
eco-wizard new [flags]
```

## Flags (all three formats work: /x, --x, -x)

| Flag | Aliases | Argument | Description |
|------|---------|----------|-------------|
| `--version` | `-v`, `/v`, `/version` | - | Show version, build number, and build date/time |
| `--help` | `-h`, `/?`, `/help` | - | Show help message |
| `--out` | `-o`, `/o`, `/out` | `<dir>` | Output directory (default: `.`) |
| `--name` | `-n`, `/n`, `/name` | `<name>` | Project name (default: `NewProject`) |
| `--lang` | `-l`, `/l`, `/lang` | `C\|CPP` | Language (default: `C`)<br>Note: Java/Python rejected with error |
| `--type` | `-t`, `/t`, `/type` | `APP\|LIB\|COM\|ECOOS\|LINUX\|BOOT` | Project type |
| `--env` | `-e`, `/e`, `/env`, `/from-env`, `--from-env` | (boolean) | Use `$(ECO_FRAMEWORK)` env path |
| `--opt` | `--options`, `/opt`, `/options` | `<csv>` | Options: `pn,cp,ai,ao,co,ut,ts` |

## Type Mapping

| CLI Value | Internal appType |
|-----------|-----------------|
| `APP` | Application |
| `LIB` | Library |
| `COM` | Component |
| `ECOOS` | Microkernel |
| `LINUX` | Kernel |
| `BOOT` | Bootloader |

## Options (--opt)

Detailed descriptions:

| Code | Name | Description |
|------|------|-------------|
| `pn` | postfix namespace | Add namespace postfix to identifiers |
| `cp` | connection points | Generate COM connection points support |
| `ai` | aggregation inner | Add inner aggregation support |
| `ao` | aggregation outer | Add outer aggregation support |
| `co` | containment outer | Add outer containment support |
| `ut` | unit test project | Generate unit test project structure |
| `ts` | thread safe | Generate thread-safe code |

Usage:
```cmd
# Single option
eco-wizard new -n MyComp -t COM -l C --opt ut

# Multiple options (comma-separated, no spaces)
eco-wizard new -n MyComp -t COM -l C --opt pn,cp,ut,ts
```

## Examples

### Check Version
```cmd
eco-wizard -v
eco-wizard --version
```

Output:
```
Eco Wizard CLI
Version:     0.1.0
Build:       #local
Build Date:  01/15/2025
Build Time:  14:23:45
```

### Minimal Component (C)
```cmd
eco-wizard new -o C:\Projects -n Eco.MyComponent -t COM -l C
```

### Component with Options
```cmd
eco-wizard new -o ./output -n Eco.List1 -t COM -l C --opt pn,cp,ut
```

### C++ Library with Env Path
```cmd
eco-wizard new --out ./libs --name Eco.Math --type LIB --lang CPP --env true
```

### Using Slash Syntax (Windows-style)
```cmd
eco-wizard new /o C:\Dev /n Eco.Test /t APP /l C
```

## Output

CLI prints:
```
✓ Project created: C:\Dev\Eco.Test
✓ Workspace: C:\Dev\Eco.Test\AssemblyFiles\Windows\MSVC_v140\EcoTest.code-workspace
```

## Error Messages

- **Unsupported language**: Java/Python validation error
- **Invalid project type**: Unknown type code
- **Missing flags**: Uses defaults (no error)

## Help

```cmd
eco-wizard --help
eco-wizard -h
eco-wizard /?
```

Shows:
```
Eco Wizard CLI - Project Generator
Version: 0.1.0 (build #local, 01/15/2025, 14:23:45)

Usage:
  eco-wizard new [options]

Options:
  -v, --version             Show version information
  -h, --help                Show this help message
  -o, --out <dir>           Output directory (default: .)
  -n, --name <name>         Project name (default: NewProject)
  -l, --lang <C|CPP>        Language: C, CPP (default: C)
  -t, --type <type>         Project type: APP, LIB, COM, ECOOS, LINUX, BOOT
  -e, --env, --from-env     Use environment path $(ECO_FRAMEWORK)
  --opt, --options <opts>   Comma-separated: pn,cp,ai,ao,co,ut,ts

Example:
  eco-wizard new -o ./out -n Eco.List1 -t COM -l C --opt pn,cp,ut
```

## For AI Agents

Call as subprocess:
```javascript
const { exec } = require('child_process');
exec('eco-wizard.exe new -o ./proj -n Eco.AI -t COM -l C --opt ut', 
  (error, stdout, stderr) => {
    if (error) console.error(error);
    console.log(stdout);
  }
);
```

Or use with spawn for streaming:
```javascript
const { spawn } = require('child_process');
const proc = spawn('eco-wizard.exe', [
  'new', '-o', './proj', '-n', 'Eco.AI', '-t', 'COM', '-l', 'C'
]);
proc.stdout.on('data', (data) => console.log(data.toString()));
```

## Notes

- All flags optional except practical workflow needs name & type
- Templates bundled in exe at compile time
- No network/installation required after build
- Windows: ~50MB exe, Mac/Linux: smaller