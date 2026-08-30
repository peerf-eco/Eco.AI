# ACOM Harness Optimization Plan

**Session Analyzed:** 8c3431c2 (Eco.TrigTable - sin/cos table 0-90°)  
**Analysis Date:** 2026-08-30  
**Target:** Reduce turns, tokens, and total time for ACOM component assembly

## Executive Summary

**Current Performance:**
- **Total Duration:** 431 seconds (7.2 minutes)
- **Total Turns:** 19 (4 architect + 13 coder + 2 tester)
- **Total Tokens:** 781,413 tokens
- **Total Cost:** $0.0517
- **Cache Hit Rate:** 71.7% architect, 82.0% coder, 48.7% tester

**Key Issues Identified:**
1. **LOW CACHE HIT RATES** — Architect (71.7%) and Tester (48.7%) well below 90% target
2. **EXCESSIVE CODER ITERATIONS** — 13 turns vs expected 3-8 turns
3. **HIGH REASONING OVERHEAD** — 76% of architect output tokens are reasoning

---

## Detailed Analysis

### 1. Token Usage Breakdown

| Role | Turns | Total Tokens | Input | Output | Cache Hit % | Cost |
|------|-------|-------------|-------|--------|------------|------|
| Architect | 4 | 168,414 | 158,079 | 10,335 | 71.7% | $0.0151 |
| Coder | 13 | 548,838 | 543,450 | 5,388 | 82.0% | $0.0308 |
| Tester | 2 | 64,161 | 63,121 | 1,040 | 48.7% | $0.0058 |
| **TOTAL** | **19** | **781,413** | **764,650** | **16,763** | **76.5%** | **$0.0517** |

### 2. Tool Usage Analysis

**Architect (10 total calls):**
- `read_component_profile`: 5x
- `search_marketplace`: 1x
- `glob`: 1x
- `read_file`: 1x
- `grep`: 1x
- `to_coder`: 1x

**Coder (18 total calls):**
- `list_dir`: 8x ⚠️ **HIGH** - Too many directory listings
- `glob`: 3x
- `run_build`: 2x
- `eco_wizard`: 1x
- `write_file`: 1x
- `read`: 1x
- `read_file`: 1x
- `to_tester`: 1x

**Tester (2 total calls):**
- `run_artifact`: 1x
- `done`: 1x

### 3. Critical Issues

#### Issue #1: Low Cache Hit Rate (HIGH PRIORITY)
**Problem:**
- Architect: 71.7% cache hit (wasted ~44,799 tokens)
- Tester: 48.7% cache hit (wasted ~32,401 tokens)
- Target: >90% cache hit rate

**Root Causes:**
1. Dynamic content injected into static system prompt sections
2. Timestamp/session IDs in prompts
3. Unstable prompt ordering
4. Context window variations between turns

**Evidence from traces:**
- Turn 1 (Architect): 0% cache hit (cold start - expected)
- Turn 2 (Architect): 95.5% cache hit ✓
- Turn 5 (Coder): Only 6.0% cache hit ⚠️ **CRITICAL**
- Turn 11 (Coder): 0% cache hit ⚠️ **CRITICAL**
- Turn 18 (Tester): 0% cache hit ⚠️ **CRITICAL**

**Impact:**
- ~77K wasted tokens per session
- ~$0.005 wasted cost per session
- 15-20% slower execution

#### Issue #2: Excessive Coder Iterations (HIGH PRIORITY)
**Problem:**
- 13 coder turns vs expected 3-8 turns
- 5-8 extra iterations = ~200 extra seconds
- Multiple build-fix cycles indicate missing information

**Root Causes:**
1. Plan lacks sufficient detail (build paths, exact includes, link flags)
2. Coder makes 8x `list_dir` calls exploring the workspace
3. Build errors not caught by plan validation
4. Missing library paths / linker configuration

**Evidence from traces:**
- Turns 5-6: eco_wizard + list_dir (project setup)
- Turns 7-10: Multiple list_dir + write_file (exploration)
- Turn 12: run_build (first attempt)
- Turn 16: run_build (second attempt)
- Turn 17: to_tester (finally done)

**Pattern:** Coder spent 6 turns (7-12) exploring and writing before first build attempt

#### Issue #3: High Reasoning Token Overhead (MEDIUM PRIORITY)
**Problem:**
- Architect: 7,862 reasoning tokens (76% of 10,335 output)
- Excessive internal thinking time

**Root Causes:**
1. Ambiguous instructions requiring extended deliberation
2. Complex ACOM architecture needs clarification
3. Lack of clear decision trees

**Impact:**
- Slower first turns
- Higher reasoning model costs

#### Issue #4: Repetitive Tool Usage (MEDIUM PRIORITY)
**Problem:**
- Coder calls `list_dir` 8 times
- Multiple glob operations for same patterns

**Root Causes:**
1. Missing workspace layout in handoff
2. No cached file tree
3. Re-discovering paths already explored

---

## Optimization Strategy

### Phase 1: Cache Hit Rate Optimization (Est. 30% token reduction)

**Goal:** Increase cache hit rates to >90% for all roles

#### 1.1 Stabilize System Prompt Structure
**Files to modify:**
- `agent/context/assembler.py`
- `agent/internal/agents/*.py`

**Changes:**
```python
# BEFORE (dynamic content in static sections)
system_prompt = f"""
=== ROLE INSTRUCTIONS ===
Current time: {datetime.now()}
Session ID: {session_id}
...
"""

# AFTER (stable, cacheable sections)
system_prompt = """
=== ROLE INSTRUCTIONS ===
...
"""
# Dynamic content goes in message history, NOT system prompt
```

**Implementation:**
1. Remove timestamps from system prompt
2. Move session IDs to user message
3. Move project_dir paths to user message
4. Ensure fixed concatenation order (already correct per docs)

**Expected Impact:**
- Architect cache hit: 71.7% → 95%
- Tester cache hit: 48.7% → 95%
- Token savings: ~77K → ~15K wasted tokens (80% reduction)

#### 1.2 Eliminate Dynamic Source Stitching Variations
**File:** `agent/context/assembler.py`

**Analysis:**
The Eco.Core1 source stitch is already stable (curated, deterministic), but timing of when it's fetched may vary.

**Changes:**
1. Pre-compute source stitch hash
2. Cache stitched sources per `(ECO_FRAMEWORK version, source_roots hash)`
3. Ensure byte-identical output across sessions

**Expected Impact:**
- Consistent Eco.Core1 block → better cache reuse
- Faster agent initialization

#### 1.3 Fix Handoff Message Structure
**Files:** `agent/internal/agents/architect.py`, `agent/internal/agents/coder.py`

**Problem:** Handoff messages may include variable content (timestamps, debugging info)

**Changes:**
```python
# BEFORE
handoff_msg = f"""
Plan generated at {now}
Total research time: {elapsed}s
...
"""

# AFTER
handoff_msg = """
=== Plan (deterministic sections only) ===
...
"""
# Timing info → separate metadata message if needed
```

**Expected Impact:**
- Coder turn 5 cache hit: 6.0% → 90%
- Coder turn 11 cache hit: 0% → 90%

### Phase 2: Reduce Coder Iterations (Est. 40% time reduction)

**Goal:** Reduce coder turns from 13 → 5-7 turns

#### 2.1 Enhance Plan Completeness
**File:** `config/prompts/architect.md`

**Add to plan template:**
```markdown
## Build Configuration (MUST include in plan)
- Exact include paths: `-I marketplace_cache/Eco.Core1/SharedFiles -I marketplace_cache/Eco.Math.C89/SharedFiles ...`
- Link libraries (in order): `lib00000000000000000000000053595333.a` (System1), then component libs
- Linker flags: `-lm` (if using math functions)
- Compiler flags: `-std=gnu89 -DECO_LINUX -DECO_X86_64`

## File Locations (cached from read_component_profile, include in plan)
- Eco.Math.C89 static lib: /app/Eco.Toolchain/Eco.AI.Assembly1/marketplace_cache/Eco.Math.C89/BuildFiles/Linux/x86_64/StaticRelease/lib<CID>.a
- ...
```

**Implementation:**
1. Architect must call `glob` to find `.a` files for each component
2. Include full paths in plan
3. Coder receives build-ready configuration

**Expected Impact:**
- Eliminates 6 exploration turns (turns 7-12)
- Coder starts writing code immediately after eco_wizard
- First build attempt on turn 2-3 instead of turn 8

#### 2.2 Add Plan Validation Gate
**New file:** `agent/internal/gates/plan_validator.py`

**Gate checks before `to_coder`:**
```python
class PlanValidator:
    def validate(self, plan_text: str) -> ValidationResult:
        errors = []
        
        # Check 1: All CIDs have factory symbols
        if "CID_Eco" in plan and "GetIEcoComponentFactoryPtr" not in plan:
            errors.append("Missing factory symbol for CID")
        
        # Check 2: Link libraries listed in dependency order
        if "lib" in plan and "Eco.System1" not in plan:
            errors.append("Missing Eco.System1 unikernel link")
        
        # Check 3: Include paths present
        if "-I" not in plan and "SharedFiles" in plan:
            errors.append("Component locations found but -I paths not specified")
        
        # Check 4: Plan size under HARNESS_PLAN_HANDOFF_MAX_BYTES
        if len(plan_text.encode()) > self.max_bytes:
            errors.append(f"Plan exceeds {self.max_bytes} bytes")
        
        return ValidationResult(valid=len(errors)==0, errors=errors)
```

**Integration:**
- Add to `to_coder` tool execution
- Block handoff if validation fails
- Architect gets errors and must fix

**Expected Impact:**
- Catch incomplete plans before coder starts
- Reduce coder error recovery turns by 2-3

#### 2.3 Improve Build Error Feedback
**File:** `agent/internal/tools/build_tool.py`

**Enhancement:**
```python
def run_build(project_dir: str, target: str = "all") -> ToolResult:
    result = subprocess.run([...], capture_output=True)
    
    if result.returncode != 0:
        # Parse common ACOM build errors
        error_hints = analyze_build_errors(result.stderr)
        
        return ToolResult(
            success=False,
            output=result.stderr,
            hints=error_hints  # e.g., "Missing header Eco.Math.C89: did you include -I path?"
        )
```

**Error patterns to detect:**
- `fatal error: IEco*.h: No such file` → "Missing -I path for component"
- `undefined reference to 'GetIEcoComponentFactoryPtr_*'` → "Missing library link"
- `multiple definition` → "Duplicate factory symbol (check link order)"

**Expected Impact:**
- Faster error recovery
- Reduced build-fix cycles from 2-3 → 1

### Phase 3: Reduce Reasoning Overhead (Est. 10% turn time reduction)

**Goal:** Reduce reasoning tokens by 30-40%

#### 3.1 Simplify Architect Prompt
**File:** `config/prompts/architect.md`

**Current:** ~8K prompt with extensive examples and decision trees  
**Target:** ~5K prompt with clear decision matrix

**Optimization:**
```markdown
# REMOVE: Verbose historical context
# REMOVE: Multiple equivalent example formats
# REMOVE: Defensive "what if" scenarios

# ADD: Decision matrix table
| Capability | Component | When to Use |
|------------|-----------|-------------|
| sin/cos/tan | Eco.Math.C89 | Trigonometry |
| printf/scanf | Eco.StdIO.C89 | Console I/O |
| pow/sqrt | Eco.Math.C89 | Math operations |

# ADD: Template for quick plan generation
```

**Expected Impact:**
- Reasoning tokens: 7,862 → ~3,000-4,000
- Faster architect turns (especially turn 1)

#### 3.2 Add On-Demand Skills for Complex Cases
**File:** `config/skills/acom_framework/SKILL.md`

**Strategy:**
- Move detailed ACOM patterns to on-demand skill
- Base prompt includes manifest only
- Agent calls `read_skill` when needed

**Frontmatter:**
```yaml
---
description: Detailed ACOM component authoring patterns and advanced scenarios
---
```

**Expected Impact:**
- System prompt: -3K tokens
- Better cache hits (smaller, more stable prompt)
- Agent loads details only when needed

### Phase 4: Tool Usage Optimization (Est. 15% turn reduction)

**Goal:** Eliminate redundant tool calls

#### 4.1 Cache Workspace Layout in Handoff
**Files:** `agent/internal/agents/architect.py`

**Add to plan:**
```markdown
## Workspace Layout (cached for coder)
project_dir: /app/Eco.Toolchain/Eco.AI.Assembly1/output/chat-ea0e66f1/Eco.TrigTable
marketplace_cache: /app/Eco.Toolchain/Eco.AI.Assembly1/marketplace_cache

Pulled components (pre-cached):
- Eco.Math.C89/
  - SharedFiles/IEcoMathC89.h, IdEcoMathC89.h
  - BuildFiles/Linux/x86_64/StaticRelease/lib00000000000000000000004D617431.a
- Eco.StdIO.C89/
  - SharedFiles/IEcoStdIOC89.h, IdEcoStdIOC89.h
  - BuildFiles/Linux/x86_64/StaticRelease/lib00000000000000000000000053494F31.a
...

Generated structure (eco_wizard):
- SourceFiles/
  - EcoMain.c
- BuildFiles/
  - Makefile
- AssemblyFiles/
```

**Expected Impact:**
- Eliminates 6-8 `list_dir` calls
- Coder knows exactly where files are

#### 4.2 Deduplicate Component Lookups
**File:** `agent/internal/tools/marketplace_tools.py`

**Add memo cache:**
```python
_component_profile_cache: Dict[str, ComponentProfile] = {}

def read_component_profile(name: str) -> ComponentProfile:
    if name in _component_profile_cache:
        return _component_profile_cache[name]
    
    profile = _load_profile(name)
    _component_profile_cache[name] = profile
    return profile
```

**Expected Impact:**
- If architect calls `read_component_profile("Eco.Math.C89")` 2x, second is instant
- Reduces redundant filesystem reads

#### 4.3 Batch Parallel Tool Calls
**File:** `config/prompts/architect.md`

**Add guidance:**
```markdown
## Tool Call Efficiency Rules
1. **Batch independent calls**: Call `read_component_profile` for all components in ONE turn, not sequentially
2. **Cache results**: Don't re-read the same component/file multiple times
3. **Progressive refinement**: grep → glob → read (coarse to fine), not random exploration
```

**Expected Impact:**
- Architect turns: 4 → 2-3
- Fewer context switches

---

## Implementation Roadmap

### Week 1: Cache Hit Rate Fixes (HIGH IMPACT)
**Priority:** P0 - Immediate 30% token reduction

1. **Day 1-2:** Stabilize system prompt structure
   - Remove timestamps/session IDs from `assembler.py`
   - Move dynamic content to message history
   - Test cache hits across 10 sample sessions

2. **Day 3:** Fix handoff message structure
   - Remove timing metadata from architect → coder handoff
   - Ensure deterministic plan format

3. **Day 4-5:** Testing & validation
   - Run 20 test sessions (simple + complex)
   - Measure cache hit rates: target >90% all roles
   - Document any remaining cache misses

**Success Metrics:**
- Architect cache hit: 71.7% → >90%
- Tester cache hit: 48.7% → >90%
- Wasted tokens: 77K → <20K per session

### Week 2: Coder Iteration Reduction (HIGH IMPACT)
**Priority:** P0 - 40% time reduction

1. **Day 1-2:** Enhance plan completeness
   - Update architect prompt template
   - Add build configuration section
   - Include cached workspace layout

2. **Day 3:** Implement plan validation gate
   - Create `PlanValidator` class
   - Integrate with `to_coder` tool
   - Add error feedback loop

3. **Day 4:** Improve build error analysis
   - Parse common ACOM build errors
   - Add contextual hints
   - Test on historical failures

4. **Day 5:** Integration testing
   - 20 test sessions
   - Measure coder turns: target 5-7 (down from 13)

**Success Metrics:**
- Coder turns: 13 → 5-7
- First build attempt: turn 8 → turn 2-3
- Build-fix cycles: 2-3 → 1

### Week 3: Reasoning & Tool Optimization (MEDIUM IMPACT)
**Priority:** P1 - 15% combined improvement

1. **Day 1-2:** Simplify architect prompt
   - Convert verbose examples to decision matrix
   - Remove redundant instructions
   - Create on-demand skill for complex patterns

2. **Day 3:** Implement tool usage optimizations
   - Add component profile cache
   - Update architect guidance for batching
   - Cache workspace layout in handoff

3. **Day 4-5:** End-to-end testing
   - 50 test sessions (mix of simple/complex tasks)
   - Compare against baseline session 8c3431c2
   - Measure all metrics

**Success Metrics:**
- Reasoning tokens: -30% (7,862 → ~5,500)
- Tool calls: -20% overall
- list_dir calls: 8 → 2-3

### Week 4: Validation & Rollout
**Priority:** P2 - Production readiness

1. **Regression testing:** 100+ diverse sessions
2. **Performance benchmarking:** Compare to baseline
3. **Documentation updates:** README, WORKING_DOCUMENTATION
4. **Rollout:** Gradual feature flag-based deployment

---

## Expected Results

### Before Optimization (Session 8c3431c2)
- Duration: 431 seconds (7.2 minutes)
- Turns: 19 (4 + 13 + 2)
- Tokens: 781,413
- Cost: $0.0517
- Cache hit: 76.5% average

### After Optimization (Projected)
- Duration: **~240 seconds (4.0 minutes)** — 44% faster
- Turns: **~10 (2 + 6 + 2)** — 47% fewer turns
- Tokens: **~420,000** — 46% token reduction
- Cost: **~$0.028** — 46% cost reduction
- Cache hit: **~92% average** — 16pp improvement

### Improvement Summary
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Duration | 431s | 240s | **-44%** ⚡ |
| Turns | 19 | 10 | **-47%** ⚡ |
| Tokens | 781K | 420K | **-46%** ⚡ |
| Cost | $0.052 | $0.028 | **-46%** 💰 |
| Cache Hit | 76.5% | 92% | **+16pp** 📈 |

---

## Risk Mitigation

### Risk 1: Cache Optimization Breaks Functionality
**Mitigation:**
- Comprehensive regression testing before rollout
- Feature flags for gradual deployment
- Rollback plan: revert to timestamp-based prompts

### Risk 2: Stricter Plan Validation Blocks Valid Plans
**Mitigation:**
- Start with warnings, not errors
- Collect false positive data for 2 weeks
- Refine validation rules iteratively

### Risk 3: Simplified Prompts Reduce Quality
**Mitigation:**
- A/B testing: old vs new prompts
- Quality metrics: build success rate, test pass rate
- Fallback to verbose prompts for complex tasks

---

## Monitoring & Metrics

### Key Performance Indicators (KPIs)
1. **Cache Hit Rate** (target: >90%)
   - Track per role, per turn
   - Alert if <80% for 3 consecutive sessions

2. **Turns per Role** (targets: architect 2-3, coder 5-7, tester 2-3)
   - Weekly averages
   - Percentile distribution (p50, p95, p99)

3. **Time to First Build** (target: <60s)
   - From session start to first `run_build` call

4. **Build Success Rate** (target: >80% first attempt)
   - First build success without errors

5. **Token Efficiency** (target: <450K per simple app)
   - Track by app complexity level

### Logging & Tracing
**Add to trace files:**
```json
{
  "optimization_version": "v2.0",
  "cache_effectiveness": {
    "hit_rate": 0.92,
    "cache_read_tokens": 445696,
    "total_prompt_tokens": 543450
  },
  "plan_validation": {
    "passed": true,
    "errors": [],
    "warnings": ["Plan size: 7.8KB / 8KB limit"]
  }
}
```

### Dashboards
1. **Real-time session monitor** (Grafana/custom UI)
   - Current cache hit rates
   - Turn counts vs baselines
   - Cost tracking

2. **Weekly optimization report**
   - Aggregated metrics
   - Trend analysis
   - Outlier investigation

---

## Next Steps

1. **Immediate:** Implement Phase 1 (cache optimization) — highest ROI
2. **Week 2:** Implement Phase 2 (coder iterations) — biggest time saver
3. **Week 3:** Implement Phases 3-4 (reasoning & tools) — polish
4. **Week 4:** Validate, test, document, deploy

**Estimated engineering effort:** 2-3 engineers, 4 weeks  
**Expected ROI:** 46% cost reduction, 44% time reduction across all ACOM builds  
**Risk level:** Low (incremental changes, comprehensive testing)

---

## Appendix: Trace Analysis Details

### Turn-by-Turn Breakdown (Session 8c3431c2)

| Turn | Role | Input | Output | Cache % | Tools | Notes |
|------|------|-------|--------|---------|-------|-------|
| 01 | architect | 37,659 | 1,740 | 0% | 6 | Cold start, component discovery |
| 02 | architect | 39,423 | 855 | 95.5% | 1 | File exploration |
| 03 | architect | 39,959 | 907 | 94.7% | 2 | Deep dive into headers |
| 04 | architect | 41,038 | 6,833 | 92.2% | 1 | Plan generation & handoff |
| 05 | coder | 39,543 | 199 | 6.0% | 1 | ⚠️ Cache miss - project scaffold |
| 06 | coder | 39,655 | 32 | 99.6% | 1 | Directory exploration |
| 07 | coder | 39,700 | 59 | 99.8% | 2 | More exploration |
| 08 | coder | 39,769 | 54 | 99.8% | 2 | Still exploring |
| 09 | coder | 41,313 | 1,916 | 95.9% | 1 | Finally writing code |
| 10 | coder | 42,765 | 164 | 92.8% | 2 | Validation checks |
| 11 | coder | 43,468 | 58 | 0% | 1 | ⚠️ Cache miss - reading file |
| 12 | coder | 43,031 | 258 | 92.4% | 1 | First build attempt |
| 13 | coder | 43,208 | 131 | 92.1% | 1 | Build error analysis |
| 14 | coder | 43,220 | 985 | 95.5% | 2 | Fix exploration |
| 15 | coder | 42,715 | 392 | 96.8% | 2 | More fixes |
| 16 | coder | 41,957 | 244 | 98.8% | 1 | Second build attempt |
| 17 | coder | 43,106 | 896 | 96.5% | 1 | Success, handoff to tester |
| 18 | tester | 30,787 | 214 | 0% | 1 | ⚠️ Cache miss - first test run |
| 19 | tester | 32,334 | 826 | 95.0% | 1 | Final validation & done |

### Critical Cache Misses
- **Turn 5 (coder):** 6.0% — Handoff from architect changed prompt structure
- **Turn 11 (coder):** 0% — System prompt regenerated mid-session
- **Turn 18 (tester):** 0% — Tester cold start with different prompt

### Tool Usage Patterns
**Architect:**
- Turn 1: Batch component lookups (efficient ✓)
- Turns 2-3: Sequential exploration (could batch)
- Turn 4: Single handoff (correct ✓)

**Coder:**
- Turns 5-10: Excessive exploration (6 turns wasted)
- Turn 12: First build (should be turn 2-3)
- Turn 16: Second build (first failed)
- Pattern: Explore → Write → Build → Fix → Build → Done

**Tester:**
- Minimal turns (efficient ✓)
- Pattern: Run → Validate → Done

---

## References

1. Session trace: `/traces/ses-8c3431c2/`
2. Project: `/output/chat-ea0e66f1/Eco.TrigTable/`
3. Documentation: `README.md`, `WORKING_DOCUMENTATION.md`
4. Configuration: `config/harness.yaml`, `config/roles.yaml`, `config/budgets.yaml`
5. Related issues: None (this is baseline analysis)

**Analysis completed by:** Kiro AI (Claude Sonnet 4.5)  
**Date:** 2026-08-30  
**Version:** 1.0
