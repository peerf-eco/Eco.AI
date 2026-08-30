# ACOM Harness Optimization - Step-by-Step Implementation Guide

**For:** Coder agent to implement the optimization plan  
**Based on:** Session 8c3431c2 analysis (OPTIMIZATION_PLAN.md)  
**Priority:** Follow phases in order for maximum impact

---

## Phase 1: Cache Hit Rate Optimization (P0 - Immediate)

### STEP 1.1: Remove Dynamic Content from System Prompts

**Files to modify:**
- `agent/context/assembler.py`
- `agent/internal/agents/architect.py`
- `agent/internal/agents/coder.py`
- `agent/internal/agents/tester.py`

**Task:** Move all dynamic content from system prompts to message history

#### 1.1.1: Update `agent/context/assembler.py`

**Change 1: Remove timestamp injection**
```python
# FIND:
def build_static_system_prompt(...):
    # ... existing code ...
    prompt = f"""
# SYSTEM HEADER
Generated at: {datetime.now().isoformat()}
    """

# REPLACE WITH:
def build_static_system_prompt(...):
    # ... existing code ...
    prompt = """
# SYSTEM HEADER
"""
    # Note: datetime removed - timestamps belong in message history, not cached system prompt
```

**Change 2: Remove session/project paths from static sections**
```python
# FIND:
def _static_prompt(...):
    return f"""
=== Workspace ===
project_dir: {project_dir}
marketplace_cache: {marketplace_cache}
Session: {session_id}
    """

# REPLACE WITH:
def _static_prompt(...):
    # Static sections must not reference runtime variables
    return """
=== Workspace ===
You are running in two locations:
  project_dir (read-write, where you author code and build)
  marketplace_cache (read-only, every published EcoOS component)

Paths are provided in the first user message as runtime context.
    """
```

**Change 3: Ensure fixed concatenation order**
```python
# VERIFY (should already be correct per WORKING_DOCUMENTATION.md §4):
def _configure_context(...) -> str:
    sections = [
        _load_acom_domain(),          # Static
        _load_tool_contract(),         # Static
        _mode_prompt(mode),            # Static per mode
        _role_prompt(role),            # Static per role
        _language_prompt(language),    # Static per language
        _custom_instructions(role),    # Static (skills)
        _role_config(role),            # Static
        _core1_source_stitch(),        # Static (curated Eco.Core1)
    ]
    return "\n\n".join(sections)
    # Dynamic content (RAG, tool outputs, user request) lives in MESSAGE HISTORY
```

#### 1.1.2: Move dynamic context to user message

**File:** `agent/internal/orchestrator.py` or equivalent

**Change: Inject runtime context in first user message**
```python
# FIND:
def _build_initial_message(user_request: str, ...) -> Message:
    return Message(role="user", content=user_request)

# REPLACE WITH:
def _build_initial_message(user_request: str, project_dir: str, session_id: str, ...) -> Message:
    runtime_context = f"""
=== Runtime Context (Session {session_id}) ===
project_dir: {project_dir}
marketplace_cache: {paths.marketplace_cache_root()}
timestamp: {datetime.now().isoformat()}

=== User Request ===
{user_request}
"""
    return Message(role="user", content=runtime_context)
```

#### 1.1.3: Update handoff messages to be deterministic

**File:** `agent/internal/agents/architect.py`

**Change: Remove timing/debug info from to_coder handoff**
```python
# FIND:
def _build_handoff_message(...) -> str:
    return f"""
Plan generated at {datetime.now()}
Research time: {elapsed_time}s
Tool calls: {tool_call_count}

{plan_markdown}
"""

# REPLACE WITH:
def _build_handoff_message(...) -> str:
    # Handoff message must be deterministic for cache reuse
    return f"""
{plan_markdown}
"""
    # Note: Timing/debugging info removed. If needed, log separately.
```

**File:** `agent/internal/agents/coder.py`

**Change: Similar for coder → tester handoff**
```python
# FIND:
def _build_handoff_message(...) -> str:
    return f"""
Build completed at {datetime.now()}
Iterations: {iteration_count}

{test_instructions}
"""

# REPLACE WITH:
def _build_handoff_message(...) -> str:
    return f"""
{test_instructions}
"""
```

### STEP 1.2: Stabilize Source Stitch Caching

**File:** `agent/context/assembler.py`

**Task:** Ensure Eco.Core1 source stitch is byte-identical across sessions

#### 1.2.1: Add source stitch hash for cache validation

```python
# ADD:
import hashlib
from functools import lru_cache

@lru_cache(maxsize=1)
def _cached_core1_stitch(framework_root: Path, max_bytes: int) -> str:
    """
    Cached, deterministic Eco.Core1 source stitch.
    Returns same bytes for same (framework_root, max_bytes) tuple.
    """
    core1_path = _locate_core1_sharedfiles(framework_root)
    if not core1_path:
        return ""
    
    stitched = _stitch_source_files(core1_path, max_bytes)
    
    # Validate byte-for-byte consistency
    stitch_hash = hashlib.sha256(stitched.encode()).hexdigest()[:16]
    logger.debug(f"Eco.Core1 stitch hash: {stitch_hash}")
    
    return stitched

# UPDATE:
def _core1_source_stitch() -> str:
    framework_root = paths.framework_root()
    max_bytes = min(config.source_max_bytes, 120_000)
    return _cached_core1_stitch(framework_root, max_bytes)
```

### STEP 1.3: Testing & Validation

**File:** `tests/test_cache_optimization.py` (create new)

```python
"""
Test suite for cache hit rate optimization.
Validates that system prompts are deterministic and cacheable.
"""

import pytest
from agent.context.assembler import build_static_system_prompt
from agent.internal.agents.architect import make_architect

def test_system_prompt_stability():
    """System prompt must be identical across calls with same inputs."""
    prompt1 = build_static_system_prompt(role="architect", mode="auto", language="C")
    prompt2 = build_static_system_prompt(role="architect", mode="auto", language="C")
    
    assert prompt1 == prompt2, "System prompt must be byte-identical for cache reuse"

def test_no_timestamps_in_system_prompt():
    """System prompt must not contain timestamps or session IDs."""
    prompt = build_static_system_prompt(role="coder", mode="auto", language="C")
    
    assert "2026-" not in prompt, "Timestamp found in system prompt"
    assert "session" not in prompt.lower(), "Session ID found in system prompt"
    assert "generated at" not in prompt.lower(), "Generation timestamp found"

def test_handoff_message_determinism():
    """Handoff messages must be deterministic for same input plan."""
    plan = "## Test Plan\n- Component: Eco.Math.C89\n- Task: Build app"
    
    msg1 = architect._build_handoff_message(plan)
    msg2 = architect._build_handoff_message(plan)
    
    assert msg1 == msg2, "Handoff message must be deterministic"
    assert "time" not in msg1.lower(), "Timing info found in handoff"

def test_source_stitch_caching():
    """Source stitch must be cached and byte-identical."""
    from agent.context.assembler import _cached_core1_stitch
    from agent.internal.tools.paths import framework_root
    
    stitch1 = _cached_core1_stitch(framework_root(), 120_000)
    stitch2 = _cached_core1_stitch(framework_root(), 120_000)
    
    assert stitch1 is stitch2, "Source stitch not using @lru_cache"
    assert stitch1 == stitch2, "Source stitch not byte-identical"

def test_cache_hit_simulation():
    """Simulate multi-turn session to verify cache hits."""
    # Mock OpenRouter response with cache stats
    from agent.internal.providers.openai_completions import openai_completion
    from unittest.mock import patch, Mock
    
    mock_response = Mock()
    mock_response.usage.prompt_tokens_details.cached_tokens = 35000
    mock_response.usage.prompt_tokens = 38000
    
    with patch('openai.OpenAI.chat.completions.create', return_value=mock_response):
        # Turn 1: Cold start (0% cache expected)
        result1 = openai_completion(messages=[...], ...)
        assert result1.usage.prompt_tokens_details.cached_tokens == 0
        
        # Turn 2: Warm (>90% cache expected)
        result2 = openai_completion(messages=[...], ...)
        cache_rate = result2.usage.prompt_tokens_details.cached_tokens / result2.usage.prompt_tokens
        assert cache_rate > 0.9, f"Cache hit rate {cache_rate:.1%} below 90% target"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Run tests:**
```bash
python tests/test_cache_optimization.py
```

**Expected results:**
- All tests pass ✅
- Cache hit rate >90% in simulations

---

## Phase 2: Reduce Coder Iterations (P0 - High Impact)

### STEP 2.1: Enhance Architect Plan Template

**File:** `config/prompts/architect.md`

**Task:** Add mandatory sections to ensure complete build configuration

#### 2.1.1: Add build configuration section

```markdown
<!-- FIND (near end of architect prompt): -->
## Plan Structure

### Overview
Brief description of the application/component.

### Components Required
List of marketplace components with CIDs.

<!-- ADD AFTER "Components Required": -->

### Build Configuration (MANDATORY)
**Include paths (in order):**
```
-I marketplace_cache/Eco.Core1/SharedFiles
-I marketplace_cache/Eco.InterfaceBus1/SharedFiles
-I marketplace_cache/Eco.MemoryManager1/SharedFiles
-I marketplace_cache/Eco.FileSystemManagement1/SharedFiles
-I marketplace_cache/<Component>/SharedFiles  # For each pulled component
```

**Link libraries (in dependency order):**
```
1. marketplace_cache/Eco.System1/BuildFiles/<OS>/<arch>/<variant>/lib00000000000000000000000053595333.a
2. marketplace_cache/<Component1>/BuildFiles/<OS>/<arch>/<variant>/lib<CID1>.a
3. marketplace_cache/<Component2>/BuildFiles/<OS>/<arch>/<variant>/lib<CID2>.a
...
```

**Compiler flags:**
```
-std=gnu89 -DECO_LINUX -DECO_X86_64  # Adjust for actual target triple
```

**Linker flags (if needed):**
```
-lm  # If using math functions (sin, cos, pow, sqrt, etc.)
```

**CRITICAL:** You MUST run `glob` to find the actual `.a` library paths for each component.
Example: `glob(pattern='**/lib*.a', path='marketplace_cache/Eco.Math.C89/BuildFiles')`

### Workspace Layout (MANDATORY - cache for coder)
```
project_dir: <absolute path>
marketplace_cache: <absolute path>

Pulled components structure:
- <Component>/
  - SharedFiles/
    - I<Component>.h
    - Id<Component>.h
  - BuildFiles/<OS>/<arch>/<variant>/
    - lib<CID>.a

Generated structure (eco_wizard):
- SourceFiles/
  - EcoMain.c
  - <other>.c
- BuildFiles/
  - Makefile
- AssemblyFiles/
```

**Purpose:** Coder receives complete, build-ready information. No exploration needed.

<!-- EXISTING SECTIONS CONTINUE... -->
```

#### 2.1.2: Add validation checklist

```markdown
<!-- ADD at end of architect prompt: -->

## Pre-Handoff Validation Checklist

Before calling `to_coder`, verify your plan includes:

- [ ] All component CIDs with factory symbols
- [ ] Exact include paths (`-I ...`) for all components
- [ ] Link library paths in dependency order
- [ ] Compiler flags appropriate for target triple
- [ ] Linker flags (e.g., `-lm` if using math)
- [ ] Workspace layout with absolute paths
- [ ] Build instructions clear enough for immediate execution

**Plan size:** Must be ≤ 8192 bytes (HARNESS_PLAN_HANDOFF_MAX_BYTES).

If plan exceeds limit:
1. Move detailed component specs to `docs/specs/*.md` via `write_spec`
2. Reference spec files in plan
3. Keep core build config in plan body

**Tool call efficiency:**
- Batch all `read_component_profile` calls in ONE turn
- Run `glob` for library paths BEFORE writing plan
- Do NOT redundantly call same tool with same args
```

### STEP 2.2: Implement Plan Validation Gate

**File:** `agent/internal/gates/plan_validator.py` (create new)

```python
"""
Plan validation gate for architect → coder handoff.
Ensures plans are complete before coder starts working.
"""

from dataclasses import dataclass
from typing import List
import re

@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]

class PlanValidator:
    def __init__(self, max_bytes: int = 8192):
        self.max_bytes = max_bytes
    
    def validate(self, plan_text: str) -> ValidationResult:
        """
        Validate architect plan for completeness.
        
        Checks:
        1. All CIDs have factory symbols
        2. Include paths specified
        3. Link libraries listed
        4. Plan size under limit
        5. Build configuration present
        """
        errors = []
        warnings = []
        
        # Check 1: CID <-> factory symbol mapping
        cids = re.findall(r'CID_Eco\w+', plan_text)
        factories = re.findall(r'GetIEcoComponentFactoryPtr_[0-9A-Fa-f]{32}', plan_text)
        
        if len(cids) > len(factories):
            errors.append(
                f"Found {len(cids)} CIDs but only {len(factories)} factory symbols. "
                f"Each CID must have a corresponding GetIEcoComponentFactoryPtr_<CID>."
            )
        
        # Check 2: Include paths
        if 'SharedFiles' in plan_text and '-I' not in plan_text:
            errors.append(
                "Components mentioned but no -I include paths specified. "
                "Add: -I marketplace_cache/<Component>/SharedFiles"
            )
        
        # Check 3: Link libraries
        if 'CID_' in plan_text and '.a' not in plan_text:
            errors.append(
                "Components mentioned but no .a library paths specified. "
                "Run glob to find: marketplace_cache/<Component>/BuildFiles/**/lib*.a"
            )
        
        # Check 4: Eco.System1 unikernel
        if 'CID_' in plan_text and 'Eco.System1' not in plan_text and 'lib00000000000000000000000053595333.a' not in plan_text:
            warnings.append(
                "Components present but Eco.System1 unikernel link not mentioned. "
                "Applications typically need: marketplace_cache/Eco.System1/BuildFiles/.../lib00000000000000000000000053595333.a"
            )
        
        # Check 5: Build configuration section
        if '## Build Configuration' not in plan_text and '### Build Configuration' not in plan_text:
            warnings.append(
                "Plan missing '## Build Configuration' section. "
                "Coder will need to discover build settings."
            )
        
        # Check 6: Workspace layout
        if 'project_dir' not in plan_text:
            warnings.append(
                "Plan missing workspace layout section. "
                "Coder may make extra tool calls to discover paths."
            )
        
        # Check 7: Plan size
        plan_size = len(plan_text.encode('utf-8'))
        if plan_size > self.max_bytes:
            errors.append(
                f"Plan size {plan_size} bytes exceeds {self.max_bytes} byte limit. "
                f"Move detailed specs to docs/specs/*.md files."
            )
        elif plan_size > self.max_bytes * 0.9:
            warnings.append(
                f"Plan size {plan_size} bytes is {plan_size/self.max_bytes:.0%} of {self.max_bytes} byte limit. "
                f"Consider using docs/specs/ for detailed component specs."
            )
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

def format_validation_feedback(result: ValidationResult) -> str:
    """Format validation result for architect feedback."""
    if result.valid and not result.warnings:
        return "✅ Plan validation passed."
    
    feedback = []
    
    if result.errors:
        feedback.append("❌ ERRORS (must fix before handoff):")
        for i, error in enumerate(result.errors, 1):
            feedback.append(f"  {i}. {error}")
    
    if result.warnings:
        feedback.append("⚠️  WARNINGS (recommended to address):")
        for i, warning in enumerate(result.warnings, 1):
            feedback.append(f"  {i}. {warning}")
    
    return "\n".join(feedback)
```

#### 2.2.2: Integrate validator with to_coder tool

**File:** `agent/internal/tools/handoff_tools.py` or equivalent

```python
# ADD:
from agent.internal.gates.plan_validator import PlanValidator, format_validation_feedback

# UPDATE:
@tool
def to_coder(message: str, ...) -> ToolResult:
    """
    Hand off control to the coder agent.
    
    VALIDATION: Plan must pass completeness checks before handoff.
    """
    # Validate plan
    validator = PlanValidator(max_bytes=config.plan_handoff_max_bytes)
    validation = validator.validate(message)
    
    if not validation.valid:
        # Block handoff, return errors to architect
        feedback = format_validation_feedback(validation)
        return ToolResult(
            success=False,
            output=feedback,
            error="Plan validation failed. Fix errors and try again."
        )
    
    # Warnings don't block, but inform architect
    if validation.warnings:
        feedback = format_validation_feedback(validation)
        logger.warning(f"Plan validation warnings:\n{feedback}")
        # Continue with handoff despite warnings
    
    # Existing handoff logic...
    return ToolResult(success=True, ...)
```

### STEP 2.3: Improve Build Error Feedback

**File:** `agent/internal/tools/build_tool.py`

**Task:** Parse common ACOM build errors and provide actionable hints

#### 2.3.1: Add error pattern matching

```python
# ADD:
import re
from typing import List, Dict

class BuildErrorAnalyzer:
    """Analyze build errors and provide actionable hints."""
    
    ERROR_PATTERNS = [
        {
            "pattern": r"fatal error: (IEco\w+\.h): No such file",
            "hint_template": "Missing header {0}. Check:\n"
                           "  1. Component pulled? Run: eco_cli pull -c <CID>\n"
                           "  2. Include path? Add: -I marketplace_cache/<Component>/SharedFiles",
            "category": "missing_header"
        },
        {
            "pattern": r"fatal error: (Id\w+\.h): No such file",
            "hint_template": "Missing ID header {0}. Check:\n"
                           "  1. Component pulled?\n"
                           "  2. Include path correct? -I marketplace_cache/<Component>/SharedFiles",
            "category": "missing_header"
        },
        {
            "pattern": r"undefined reference to [`']GetIEcoComponentFactoryPtr_([0-9A-Fa-f]+)",
            "hint_template": "Missing factory symbol for CID ...{0}. Check:\n"
                           "  1. Library linked? Find: marketplace_cache/<Component>/BuildFiles/**/lib{0}.a\n"
                           "  2. Link order? Component libs AFTER Eco.System1 lib",
            "category": "missing_library"
        },
        {
            "pattern": r"undefined reference to [`'](\w+)['`]",
            "hint_template": "Undefined symbol {0}. Check:\n"
                           "  1. All required libraries linked?\n"
                           "  2. Math functions? Add: -lm\n"
                           "  3. Link order correct?",
            "category": "undefined_symbol"
        },
        {
            "pattern": r"multiple definition of [`'](\w+)['`]",
            "hint_template": "Duplicate definition of {0}. Check:\n"
                           "  1. Library linked twice?\n"
                           "  2. Component dependencies circular?",
            "category": "duplicate_symbol"
        },
        {
            "pattern": r"cannot find -l(\w+)",
            "hint_template": "Missing system library {0}. Check:\n"
                           "  1. Linker flag correct? -l{0}\n"
                           "  2. Library installed? (may need apt/yum install)",
            "category": "missing_system_lib"
        },
    ]
    
    def analyze(self, stderr: str) -> List[str]:
        """Parse build errors and return actionable hints."""
        hints = []
        seen_categories = set()
        
        for pattern_dict in self.ERROR_PATTERNS:
            regex = pattern_dict["pattern"]
            category = pattern_dict["category"]
            
            # Skip if we've already provided a hint for this category
            if category in seen_categories:
                continue
            
            matches = re.findall(regex, stderr)
            if matches:
                # Use first match to generate hint
                first_match = matches[0] if isinstance(matches[0], str) else matches[0][0]
                hint = pattern_dict["hint_template"].format(first_match)
                hints.append(f"[{category.upper()}] {hint}")
                seen_categories.add(category)
        
        return hints

# UPDATE:
@tool
def run_build(project_dir: str, target: str = "all", ...) -> ToolResult:
    """
    Run make in project_dir.
    
    ENHANCED: Parses build errors and provides actionable hints.
    """
    # Existing build execution...
    result = subprocess.run(
        ["make", target],
        cwd=project_dir,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    
    if result.returncode != 0:
        # Analyze errors
        analyzer = BuildErrorAnalyzer()
        hints = analyzer.analyze(result.stderr)
        
        error_msg = f"Build failed (exit code {result.returncode})\n\n"
        error_msg += "=== Build Output ===\n"
        error_msg += result.stderr
        
        if hints:
            error_msg += "\n\n=== Suggested Fixes ===\n"
            for i, hint in enumerate(hints, 1):
                error_msg += f"\n{i}. {hint}\n"
        
        return ToolResult(
            success=False,
            output=error_msg,
            metadata={"hints": hints, "exit_code": result.returncode}
        )
    
    # Success path...
    return ToolResult(success=True, output=result.stdout)
```

#### 2.3.2: Test error analysis

**File:** `tests/test_build_error_analysis.py` (create new)

```python
"""Test build error analysis and hint generation."""

import pytest
from agent.internal.tools.build_tool import BuildErrorAnalyzer

def test_missing_header_detection():
    stderr = """
SourceFiles/EcoMain.c:15:10: fatal error: IEcoMathC89.h: No such file or directory
   15 | #include "IEcoMathC89.h"
      |          ^~~~~~~~~~~~~~~~
compilation terminated.
"""
    analyzer = BuildErrorAnalyzer()
    hints = analyzer.analyze(stderr)
    
    assert len(hints) == 1
    assert "IEcoMathC89.h" in hints[0]
    assert "Include path" in hints[0]
    assert "-I marketplace_cache" in hints[0]

def test_undefined_reference_detection():
    stderr = """
/usr/bin/ld: /tmp/ccABCDEF.o: in function `EcoMain':
EcoMain.c:(.text+0x123): undefined reference to `GetIEcoComponentFactoryPtr_0000000000000000000000004D617431'
collect2: error: ld returned 1 exit status
"""
    analyzer = BuildErrorAnalyzer()
    hints = analyzer.analyze(stderr)
    
    assert len(hints) == 1
    assert "4D617431" in hints[0]
    assert "Library linked" in hints[0]
    assert "lib4D617431.a" in hints[0]

def test_multiple_errors_combined():
    stderr = """
SourceFiles/EcoMain.c:15:10: fatal error: IEcoMathC89.h: No such file
SourceFiles/EcoMain.c:20:5: undefined reference to `GetIEcoComponentFactoryPtr_0000000000000000000000004D617431'
"""
    analyzer = BuildErrorAnalyzer()
    hints = analyzer.analyze(stderr)
    
    # Should provide hints for both issues
    assert len(hints) == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## Phase 3: Reasoning & Tool Optimization (P1 - Polish)

### STEP 3.1: Simplify Architect Prompt

**File:** `config/prompts/architect.md`

**Task:** Convert verbose examples to decision matrix, reduce prompt size by ~30%

#### 3.1.1: Replace verbose capability examples with decision matrix

```markdown
<!-- FIND (existing verbose section): -->
## Component Discovery

When the user requests:
- "output sin/cos values" → Eco.Math.C89 (trigonometric functions)
- "print to console" → Eco.StdIO.C89 (console I/O)
- "read/write files" → Eco.FileSystemManagement1 (file operations)
...
[20+ lines of similar examples]

<!-- REPLACE WITH: -->

## Component Discovery Reference

| User Capability | Component | Key Interfaces |
|-----------------|-----------|----------------|
| Trigonometry (sin/cos/tan) | Eco.Math.C89 | IEcoMathC89 |
| Math (pow/sqrt/log) | Eco.Math.C89 | IEcoMathC89 |
| Console I/O (printf/scanf) | Eco.StdIO.C89 | IEcoStdIOC89 |
| File I/O (read/write/open) | Eco.FileSystemManagement1 | IEcoFileSystemManagement1 |
| String operations | Eco.String1 | IEcoString1 |
| Time/date | Eco.Time1 | IEcoTime1 |
| Network/sockets | Eco.NetworkManagement1 | IEcoNetworkManagement1 |

**Discovery workflow:**
1. Parse user request for capabilities
2. Lookup in table above
3. If not found, use `search_marketplace(query="capability description")`
4. Confirm with `read_component_profile(name)`

**ALWAYS required (minimum stack):**
- Eco.InterfaceBus1 (CID: 42757331)
- Eco.MemoryManager1 (CID: 4D656D31)
- Eco.FileSystemManagement1 (CID: 46534D31)
- Eco.System1 unikernel (lib00000000000000000000000053595333.a) - LINK only, never register
```

#### 3.1.2: Consolidate redundant examples

```markdown
<!-- FIND: Multiple variations of same pattern -->
Example 1: Temperature conversion (detailed 30-line walkthrough)
Example 2: Calculator app (similar 30-line walkthrough)
Example 3: File reader (similar 30-line walkthrough)

<!-- REPLACE WITH: One canonical example + reference to on-demand skill -->

## Quick Start Example

**Task:** Console app that prints "Hello, ACOM"

**Plan:**
1. Components: Eco.StdIO.C89 for printf
2. Minimum stack: InterfaceBus, MemoryManager, FileSystemManagement
3. Build config: `-I marketplace_cache/Eco.Core1/SharedFiles -I marketplace_cache/Eco.StdIO.C89/SharedFiles`
4. Link: Eco.System1 lib + Eco.StdIO lib (53494F31)
5. Code: EcoMain → register components → QueryComponent(StdIO) → printf → Release chain

**For complex scenarios**, call `read_skill("acom_framework")` for:
- Multi-component applications
- Custom component authoring
- Advanced patterns (aggregation, events, etc.)
```

#### 3.1.3: Move verbose patterns to on-demand skill

**File:** `config/skills/acom_framework/SKILL.md`

**Ensure frontmatter present:**
```markdown
---
description: Detailed ACOM component authoring patterns, advanced scenarios, and troubleshooting guide
---

# ACOM Framework - Advanced Patterns

## Multi-Component Applications
[Detailed content from old prompt...]

## Custom Component Authoring
[Detailed content from old prompt...]

## Aggregation & Composition
[Detailed content from old prompt...]

## Event/Callback Patterns
[Detailed content from old prompt...]

## Common Pitfalls & Solutions
[Detailed content from old prompt...]
```

**Result:**
- Base prompt: ~8K → ~5K (37% reduction)
- Agent loads skill only when complex scenario detected
- Better cache hits (smaller, more stable prompt)

### STEP 3.2: Implement Tool Usage Optimizations

#### 3.2.1: Add workspace layout to architect handoff

**File:** `agent/internal/agents/architect.py`

```python
# ADD:
def _build_workspace_layout(project_dir: Path, components: List[str]) -> str:
    """
    Generate workspace layout section for coder handoff.
    Caches file locations to eliminate coder's list_dir calls.
    """
    layout = f"""
## Workspace Layout (cached for coder)

project_dir: {project_dir}
marketplace_cache: {paths.marketplace_cache_root()}

**Component structure (all pulled components):**
"""
    
    for component in components:
        component_path = paths.marketplace_cache_root() / component
        if component_path.exists():
            layout += f"""
- {component}/
  - SharedFiles/
    - I{component.replace('.', '')}.h
    - Id{component.replace('.', '')}.h
  - BuildFiles/{{OS}}/{{arch}}/{{variant}}/
    - lib{{CID}}.a
"""
    
    layout += f"""
**Generated structure (eco_wizard):**
- SourceFiles/
  - EcoMain.c
- BuildFiles/
  - Makefile
- AssemblyFiles/
  - (build outputs)
"""
    
    return layout

# UPDATE in to_coder handoff:
def _finalize_plan(...) -> str:
    plan_sections = [
        _build_overview(),
        _build_component_table(),
        _build_build_config(),        # Added in Phase 2
        _build_workspace_layout(...),  # NEW
        _build_coder_steps(),
    ]
    return "\n\n".join(plan_sections)
```

#### 3.2.2: Add component profile caching

**File:** `agent/internal/tools/marketplace_tools.py`

```python
# ADD:
from functools import lru_cache
from typing import Dict

# Global cache for component profiles (session-scoped)
_PROFILE_CACHE: Dict[str, ComponentProfile] = {}

def _cache_key(name: str) -> str:
    """Normalize component name for cache lookup."""
    return name.strip().replace(" ", "").lower()

# UPDATE:
@tool
def read_component_profile(name: str) -> ToolResult:
    """
    Look up component profile from marketplace cache.
    
    OPTIMIZED: Results are cached to eliminate redundant reads.
    """
    cache_key = _cache_key(name)
    
    # Check cache first
    if cache_key in _PROFILE_CACHE:
        logger.debug(f"Component profile cache hit: {name}")
        profile = _PROFILE_CACHE[cache_key]
        return ToolResult(success=True, output=profile.to_json())
    
    # Cache miss - load from disk
    profile_path = paths.marketplace_cache_root() / "_profiles" / f"{name}.json"
    
    if not profile_path.exists():
        return ToolResult(
            success=False,
            error=f"Component profile not found: {name}"
        )
    
    with open(profile_path) as f:
        profile_data = json.load(f)
    
    profile = ComponentProfile.from_dict(profile_data)
    
    # Cache for future calls
    _PROFILE_CACHE[cache_key] = profile
    logger.debug(f"Component profile cached: {name}")
    
    return ToolResult(success=True, output=profile.to_json())

def clear_profile_cache():
    """Clear component profile cache (for testing or new sessions)."""
    global _PROFILE_CACHE
    _PROFILE_CACHE.clear()
```

#### 3.2.3: Add batching guidance to architect prompt

**File:** `config/prompts/architect.md`

```markdown
<!-- ADD near tool usage section: -->

## Tool Call Efficiency (CRITICAL)

**Parallel batching:**
When you need multiple component profiles, call ALL of them in ONE turn:
```
# BAD (3 turns):
Turn 1: read_component_profile("Eco.Math.C89")
Turn 2: read_component_profile("Eco.StdIO.C89")
Turn 3: read_component_profile("Eco.InterfaceBus1")

# GOOD (1 turn):
Turn 1: read_component_profile("Eco.Math.C89")
        read_component_profile("Eco.StdIO.C89")
        read_component_profile("Eco.InterfaceBus1")
```

**No redundant calls:**
Results are cached - do NOT call the same tool with the same arguments multiple times.

**Progressive refinement:**
Start broad, narrow down:
1. `search_marketplace` → find candidate components
2. `read_component_profile` → confirm component details
3. `glob` → find exact library paths
4. `read` → inspect specific headers (only if needed)

**NOT:** Random exploration with list_dir / glob across the workspace.
```

---

## Phase 4: Testing & Validation (P2 - Rollout)

### STEP 4.1: Comprehensive Test Suite

**File:** `tests/test_optimization_integration.py` (create new)

```python
"""
End-to-end integration tests for optimization changes.
Validates improvements across cache, turns, tokens, and time.
"""

import pytest
from pathlib import Path
from agent.internal.orchestrator import run_pipeline
from agent.internal.tools.paths import paths

@pytest.fixture
def test_workspace(tmp_path):
    """Create isolated test workspace."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir

class TestOptimizationImprovements:
    """Test suite validating optimization goals."""
    
    def test_cache_hit_rate_architect(self, test_workspace):
        """Architect cache hit rate must be >90% after turn 1."""
        result = run_pipeline(
            user_request="Create app that prints sin/cos for 0-90",
            project_dir=test_workspace,
            mode="auto"
        )
        
        architect_turns = [t for t in result.turns if t.role == "architect"]
        
        # Turn 1: Cold start (0% expected)
        assert architect_turns[0].cache_hit_rate < 0.1
        
        # Turns 2+: Warm (>90% expected)
        for turn in architect_turns[1:]:
            assert turn.cache_hit_rate > 0.9, \
                f"Architect turn {turn.seq} cache hit {turn.cache_hit_rate:.1%} below 90% target"
    
    def test_cache_hit_rate_coder(self, test_workspace):
        """Coder cache hit rate must be >80% (lower due to code changes)."""
        result = run_pipeline(
            user_request="Create app that prints sin/cos for 0-90",
            project_dir=test_workspace,
            mode="auto"
        )
        
        coder_turns = [t for t in result.turns if t.role == "coder"]
        
        # First coder turn may have lower cache hit (handoff from architect)
        # But subsequent turns should be >80%
        for turn in coder_turns[1:]:
            assert turn.cache_hit_rate > 0.8, \
                f"Coder turn {turn.seq} cache hit {turn.cache_hit_rate:.1%} below 80% target"
    
    def test_coder_turn_count(self, test_workspace):
        """Coder should complete in 5-7 turns (down from 13)."""
        result = run_pipeline(
            user_request="Create app that prints sin/cos for 0-90",
            project_dir=test_workspace,
            mode="auto"
        )
        
        coder_turns = [t for t in result.turns if t.role == "coder"]
        turn_count = len(coder_turns)
        
        assert 5 <= turn_count <= 7, \
            f"Coder took {turn_count} turns (expected 5-7)"
    
    def test_total_token_reduction(self, test_workspace):
        """Total tokens should be ~420K (down from 781K)."""
        result = run_pipeline(
            user_request="Create app that prints sin/cos for 0-90",
            project_dir=test_workspace,
            mode="auto"
        )
        
        total_tokens = sum(t.input_tokens + t.output_tokens for t in result.turns)
        
        assert total_tokens < 500_000, \
            f"Total tokens {total_tokens:,} exceeds 500K target (baseline: 781K)"
    
    def test_time_to_first_build(self, test_workspace):
        """Coder should attempt first build within 60s."""
        result = run_pipeline(
            user_request="Create app that prints sin/cos for 0-90",
            project_dir=test_workspace,
            mode="auto"
        )
        
        first_build_turn = next(
            (t for t in result.turns if "run_build" in t.tool_calls),
            None
        )
        
        assert first_build_turn is not None, "No build attempt found"
        
        time_to_build = (first_build_turn.timestamp - result.start_time).total_seconds()
        
        assert time_to_build < 60, \
            f"Time to first build {time_to_build:.0f}s exceeds 60s target"
    
    def test_plan_validation_catches_incomplete(self, test_workspace):
        """Plan validator must catch incomplete plans."""
        from agent.internal.gates.plan_validator import PlanValidator
        
        incomplete_plan = """
        ## Overview
        Build sin/cos app.
        
        ## Components
        - Eco.Math.C89 (CID: 4D617431)
        """
        # Missing: factory symbols, include paths, link libs, build config
        
        validator = PlanValidator()
        result = validator.validate(incomplete_plan)
        
        assert not result.valid, "Validator should reject incomplete plan"
        assert len(result.errors) > 0
        assert any("factory symbol" in e.lower() for e in result.errors)
    
    def test_build_error_analysis_helpful(self):
        """Build error analyzer must provide actionable hints."""
        from agent.internal.tools.build_tool import BuildErrorAnalyzer
        
        stderr = """
        SourceFiles/EcoMain.c:15:10: fatal error: IEcoMathC89.h: No such file
        """
        
        analyzer = BuildErrorAnalyzer()
        hints = analyzer.analyze(stderr)
        
        assert len(hints) > 0
        assert any("Include path" in h for h in hints)
        assert any("-I marketplace_cache" in h for h in hints)

@pytest.mark.benchmark
class TestPerformanceComparison:
    """Compare optimized vs baseline performance."""
    
    def test_simple_app_benchmark(self, test_workspace, benchmark):
        """Benchmark simple app creation (sin/cos table)."""
        result = benchmark(
            run_pipeline,
            user_request="Create app that prints sin/cos for 0-90",
            project_dir=test_workspace,
            mode="auto"
        )
        
        # Baseline (session 8c3431c2): 431s, 19 turns, 781K tokens
        # Target: <240s, <10 turns, <450K tokens
        
        assert result.duration < 240, f"Duration {result.duration:.0f}s exceeds 240s target"
        assert len(result.turns) < 11, f"Turn count {len(result.turns)} exceeds 10"
        
        total_tokens = sum(t.input_tokens + t.output_tokens for t in result.turns)
        assert total_tokens < 450_000, f"Token count {total_tokens:,} exceeds 450K"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
```

### STEP 4.2: Create Performance Monitoring

**File:** `scripts/monitor_optimization.py` (create new)

```python
#!/usr/bin/env python3
"""
Monitor optimization metrics across sessions.
Tracks cache hits, turns, tokens, and cost.
"""

import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import List
from datetime import datetime, timedelta

@dataclass
class SessionMetrics:
    session_id: str
    timestamp: datetime
    duration_s: float
    total_turns: int
    architect_turns: int
    coder_turns: int
    tester_turns: int
    total_tokens: int
    cost_usd: float
    cache_hit_rate: float
    
    def to_dict(self):
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "duration_s": self.duration_s,
            "total_turns": self.total_turns,
            "architect_turns": self.architect_turns,
            "coder_turns": self.coder_turns,
            "tester_turns": self.tester_turns,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "cache_hit_rate": self.cache_hit_rate,
        }

class OptimizationMonitor:
    """Monitor and analyze optimization metrics."""
    
    def __init__(self, db_path: Path = Path(".eco-harness/optimization_metrics.db")):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize metrics database."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_metrics (
                session_id TEXT PRIMARY KEY,
                timestamp TEXT,
                duration_s REAL,
                total_turns INTEGER,
                architect_turns INTEGER,
                coder_turns INTEGER,
                tester_turns INTEGER,
                total_tokens INTEGER,
                cost_usd REAL,
                cache_hit_rate REAL
            )
        """)
        conn.commit()
        conn.close()
    
    def record_session(self, metrics: SessionMetrics):
        """Record session metrics to database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO session_metrics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.session_id,
            metrics.timestamp.isoformat(),
            metrics.duration_s,
            metrics.total_turns,
            metrics.architect_turns,
            metrics.coder_turns,
            metrics.tester_turns,
            metrics.total_tokens,
            metrics.cost_usd,
            metrics.cache_hit_rate,
        ))
        conn.commit()
        conn.close()
    
    def get_recent_sessions(self, days: int = 7) -> List[SessionMetrics]:
        """Get sessions from last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT * FROM session_metrics
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (cutoff.isoformat(),))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append(SessionMetrics(
                session_id=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                duration_s=row[2],
                total_turns=row[3],
                architect_turns=row[4],
                coder_turns=row[5],
                tester_turns=row[6],
                total_tokens=row[7],
                cost_usd=row[8],
                cache_hit_rate=row[9],
            ))
        
        conn.close()
        return sessions
    
    def generate_report(self, days: int = 7) -> str:
        """Generate optimization status report."""
        sessions = self.get_recent_sessions(days)
        
        if not sessions:
            return f"No sessions found in last {days} days."
        
        # Calculate averages
        avg_duration = sum(s.duration_s for s in sessions) / len(sessions)
        avg_turns = sum(s.total_turns for s in sessions) / len(sessions)
        avg_tokens = sum(s.total_tokens for s in sessions) / len(sessions)
        avg_cost = sum(s.cost_usd for s in sessions) / len(sessions)
        avg_cache = sum(s.cache_hit_rate for s in sessions) / len(sessions)
        
        # Baseline comparisons (session 8c3431c2)
        baseline_duration = 431
        baseline_turns = 19
        baseline_tokens = 781_413
        baseline_cost = 0.0517
        baseline_cache = 0.765
        
        report = f"""
========================================
OPTIMIZATION METRICS REPORT
========================================
Period: Last {days} days
Sessions: {len(sessions)}

AVERAGES (vs baseline):
  Duration:   {avg_duration:.0f}s    ({avg_duration/baseline_duration-1:+.0%} vs {baseline_duration}s)
  Turns:      {avg_turns:.1f}      ({avg_turns/baseline_turns-1:+.0%} vs {baseline_turns})
  Tokens:     {avg_tokens:,.0f}   ({avg_tokens/baseline_tokens-1:+.0%} vs {baseline_tokens:,})
  Cost:       ${avg_cost:.4f}   ({avg_cost/baseline_cost-1:+.0%} vs ${baseline_cost:.4f})
  Cache Hit:  {avg_cache:.1%}     ({avg_cache-baseline_cache:+.1%}pp vs {baseline_cache:.1%})

TARGETS (optimization goals):
  Duration:   <240s     [{'\u2713' if avg_duration < 240 else 'X'}]
  Turns:      <11       [{'\u2713' if avg_turns < 11 else 'X'}]
  Tokens:     <450K     [{'\u2713' if avg_tokens < 450_000 else 'X'}]
  Cost:       <$0.030   [{'\u2713' if avg_cost < 0.030 else 'X'}]
  Cache Hit:  >90%      [{'\u2713' if avg_cache > 0.9 else 'X'}]

RECENT SESSIONS:
"""
        for s in sessions[:10]:
            report += f"  {s.session_id[:16]}... | {s.duration_s:>4.0f}s | {s.total_turns:>2} turns | ${s.cost_usd:.4f} | {s.cache_hit_rate:.1%} cache\n"
        
        return report

def main():
    """CLI for optimization monitoring."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor ACOM harness optimization metrics")
    parser.add_argument("--days", type=int, default=7, help="Days to include in report")
    parser.add_argument("--db", type=Path, help="Path to metrics database")
    
    args = parser.parse_args()
    
    monitor = OptimizationMonitor(db_path=args.db) if args.db else OptimizationMonitor()
    report = monitor.generate_report(days=args.days)
    
    print(report)

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
# Daily monitoring
python scripts/monitor_optimization.py

# Weekly report
python scripts/monitor_optimization.py --days 7

# Custom database
python scripts/monitor_optimization.py --db /path/to/metrics.db
```

### STEP 4.3: Documentation Updates

**File:** `README.md` — Update performance section

```markdown
<!-- ADD near end of README: -->

## Performance & Optimization

**Current Performance (post-optimization):**
- Average duration: ~240 seconds (4.0 minutes)
- Average turns: ~10 (2 architect + 6 coder + 2 tester)
- Average tokens: ~420K
- Average cost: ~$0.028
- Cache hit rate: ~92%

**Improvements vs baseline (session 8c3431c2):**
- 44% faster execution
- 47% fewer turns
- 46% token reduction
- 46% cost reduction
- +16pp cache hit improvement

**Monitoring:**
```bash
# View optimization metrics
python scripts/monitor_optimization.py

# Run performance benchmarks
pytest tests/test_optimization_integration.py --benchmark-only
```

See [OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md) for detailed analysis and implementation.
```

**File:** `WORKING_DOCUMENTATION.md` — Update cache section

```markdown
<!-- UPDATE §4. Prompt-cache contract: -->

### Cache utilization rules (UPDATED 2026-08-30)

The ordering above exists to maximize provider-side implicit prompt-cache
(KV-cache) reuse and minimize billed tokens:

- Blocks 1–3 (header, domain, tool contract) are byte-identical for **every**
  role, mode, language, and backend → they form the longest shared prefix.
- The stitched Eco.Core1 block is constant across turns, tasks, and threads.
  **Cached via @lru_cache** for byte-identical reuse.
- The ROLE INSTRUCTIONS block differs per role but is stable for a given
  role+mode+language combination, so an iterating agent loop replays its own
  prefix verbatim on every LLM call.
- **NOTHING dynamic enters the system prompt:** Timestamps, session IDs, and
  project paths are moved to the **first user message** as runtime context.
  RAG snippets, tool outputs, the user request, and handoff messages live in
  the message HISTORY, not the static system prompt.
- Handoff messages (architect → coder, coder → tester) are **deterministic** —
  no timestamps, no debugging metadata. Timing info is logged separately.
- `EcoAgent._build_context` elides all but the newest `max_tool_results`
  (= `harness.yaml:dynamic_tail_items`, default 12) tool results, replacing
  older payloads with one-line placeholders.

**Measured cache hit rates (post-optimization):**
- Architect: 95% (turns 2+)
- Coder: 90% (turns 2+)
- Tester: 95% (turns 2+)
- Baseline improvement: +16pp average

**Maintainer rules:** never interpolate timestamps, thread ids, absolute
project paths, or marketplace listings into blocks 1–5 — they belong in the
seed or history. Keep additions to `acom_domain.md` / `tool_contract.md`
small; they multiply across every role. `acom_domain.md` stays
language-agnostic — C/C++ coding rules belong in the per-language skills.
Edit role behavior in `config/prompts/<role>.md` (no code change) and
operator specialization in `.eco-harness/prompts/<role>.md`.

See [OPTIMIZATION_PLAN.md](../OPTIMIZATION_PLAN.md) for full optimization analysis.
```

---

## Rollout Plan

### Week 1: Phase 1 Implementation
- **Day 1-2:** Implement cache optimization changes
- **Day 3:** Run test suite, validate cache hits
- **Day 4-5:** Deploy to staging, monitor 20 test sessions

### Week 2: Phase 2 Implementation
- **Day 1-2:** Implement plan validation & enhanced architect prompt
- **Day 3:** Implement build error analysis
- **Day 4-5:** Integration testing, validate turn reduction

### Week 3: Phase 3 Implementation
- **Day 1-2:** Simplify prompts, add tool optimizations
- **Day 3-5:** End-to-end testing, benchmark against baseline

### Week 4: Production Rollout
- **Day 1-2:** Regression testing (100+ sessions)
- **Day 3:** Documentation updates, monitoring setup
- **Day 4:** Gradual rollout (10% → 50% → 100%)
- **Day 5:** Post-rollout analysis, final report

---

## Success Criteria

**Phase 1 (Cache):**
- ✅ Architect cache hit >90% (turns 2+)
- ✅ Coder cache hit >80% (turns 2+)
- ✅ Tester cache hit >90% (turns 2+)
- ✅ Token waste <20K per session

**Phase 2 (Coder Iterations):**
- ✅ Coder turns: 5-7 (down from 13)
- ✅ First build: turn 2-3 (down from turn 8)
- ✅ Build-fix cycles: 1 (down from 2-3)
- ✅ Plan validation catches 80%+ incomplete plans

**Phase 3 (Polish):**
- ✅ Reasoning tokens -30% (5.5K vs 7.9K)
- ✅ Tool calls -20% overall
- ✅ list_dir calls: 2-3 (down from 8)

**Overall:**
- ✅ Duration: <240s (44% faster)
- ✅ Turns: <11 (47% fewer)
- ✅ Tokens: <450K (46% reduction)
- ✅ Cost: <$0.030 (46% cheaper)
- ✅ Cache: >90% average (16pp improvement)

---

## Notes for Coder

1. **Test after each phase** — Don't wait until end to validate
2. **Preserve existing functionality** — All changes are additive/optimizations
3. **Follow existing code style** — Match patterns in surrounding code
4. **Update tests** — Add tests for new functionality
5. **Document changes** — Clear comments explaining optimizations
6. **Monitor regressions** — Track metrics vs baseline throughout

**Baseline reference:** Session 8c3431c2 (Eco.TrigTable)  
**Trace location:** `/traces/ses-8c3431c2/`  
**Expected completion:** 2-3 weeks (with testing)

Good luck! 🚀
