"""Regression tests for the eco-wizard wrapper's v0.1.3+ JSON contract.

Covers: capability feature-detection (`version --json`), manifest-v1 parsing
with nested project_dir rebasing, JSON error contract (code/hint/exit_code),
the legacy text-mode fallback for pre-0.1.3 binaries, the C/CPP + ECO_FRAMEWORK
pre-checks, and the `eco_wizard_validate` tool (rc 0/3 mapping).

The tests run against a stub executable (ECO_WIZARD env) that emulates the
real 0.1.3+ CLI; the live binary itself is exercised by ops, not CI.
"""
import json
import stat

import pytest

from eco_harness.agent.internal.tools import eco_wizard as ez
from eco_harness.agent.internal.tools.eco_wizard import (
    _ValidateArgs,
    _WizardArgs,
    _run_validate,
    _run_wizard,
    _wizard_capabilities,
)

_STUB = r"""#!/usr/bin/env bash
# Emulates eco-wizard v0.1.3+ (JSON manifest contract) for wrapper tests.
mode="$1"; shift
case "$mode" in
  version)
    if [ "$1" = "--json" ] && [ "${ECO_STUB_LEGACY:-0}" != "1" ]; then
      cat <<'EOF'
{"name":"eco-wizard","version":"0.2.0-stub","capabilities":["json-output","manifest-v1","new","validate","flag.dry-run","flag.verify"],"exit_codes":{"ok":0,"usage":2,"not-found":3,"network":4,"policy-denied":5}}
EOF
      exit 0
    fi
    echo "eco-wizard 0.2.0-stub"; exit 0 ;;
  new)
    out="."; name="NewProject"; json=0; ifabsent=0; prev=""
    for a in "$@"; do
      case "$prev" in --out) out="$a";; --name) name="$a";; esac
      case "$a" in --out|--name) prev="$a";; *) prev="";; esac
      [ "$a" = "--json" ] && json=1
      [ "$a" = "--if-absent" ] && ifabsent=1
    done
    norm=$(printf '%s' "$name" | tr -d '.')
    entry="SourceFiles/${norm}.c"
    if [ "$json" = "1" ]; then
      pdir="$out/$name"
    else
      pdir="$out"
    fi
    mkdir -p "$pdir/SourceFiles"
    printf 'int16_t EcoMain(IEcoUnknown* pIUnk) { return 0; }\n' > "$pdir/$entry"
    printf '{ }\n' > "$pdir/config.json"
    if [ "$json" = 1 ] && [ "${ECO_STUB_BAD_JSON:-0}" = "1" ]; then
      printf 'not-json\n'
      exit 0
    fi
    if [ "$json" = 1 ]; then
      if [ -n "$(ls -A "$pdir" 2>/dev/null)" ] && [ "${ECO_STUB_PRE_CREATED:-0}" = "1" ] && [ "$ifabsent" = "0" ]; then
        printf '{"error":"Project directory already exists: %s","code":"POLICY_EXISTS","hint":"Use --if-absent.","exit_code":5}\n' "$pdir"
        exit 5
      fi
      status="created"; action="created"; det=false
      if [ "$ifabsent" = "1" ]; then status="reused"; action="exists"; det=true; fi
      printf '{"schema_version":1,"status":"%s","wizard_version":"0.2.0-stub","project_name":"%s","project_type":"APP","language":"C","output_dir":"%s","project_dir":"%s","entry_name":"%s","normalized_name":"%s","collision":{"detected":%s,"policy":"fail","action":"%s"},"entry_file":"%s","build_subdir":"AssemblyFiles/Linux/gcc_v132","build_file":"AssemblyFiles/Linux/gcc_v132/MakefileExe","build_command":"make -C %s/AssemblyFiles/Linux/gcc_v132 -f MakefileExe ARCH=x64","build_command_argv":["make","-C","%s/AssemblyFiles/Linux/gcc_v132","-f","MakefileExe","ARCH=x64"],"config_file":"config.json","environment_path":null,"workspace_files":[],"files":{"created":["%s","config.json"],"existing":[],"overwritten":[]},"validation":{"files_exist":true,"build_dry_run":true,"warnings":[]},"atomic":true,"warnings":[]}\n' \
         "$status" "$name" "$out" "$pdir" "$norm" "$norm" "$det" "$action" "$entry" "$pdir" "$pdir" "$entry"
      exit 0
    fi
    printf 'Status: created\nProject: %s\nEntry file: %s\n' "$pdir" "$entry"
    exit 0 ;;
  validate)
    dir="$1"; shift
    for a in "$@"; do [ "$a" = "--json" ] && json=1; done
    if [ "${ECO_STUB_BAD_VALIDATE:-0}" = "1" ]; then
      printf '{"ok":true}\n'
      exit 0
    fi
    if [ -d "$dir/SourceFiles" ]; then
      printf '{"schema_version":1,"dir":"%s","ok":true,"findings":[]}\n' "$dir"; exit 0
    fi
    printf '{"schema_version":1,"dir":"%s","ok":false,"findings":[{"severity":"error","code":"MISSING_ENTRY","message":"Entry source file not found","path":"SourceFiles/X.c"},{"severity":"warning","code":"MISSING_WORKSPACE","message":"ws","path":"w"}]}\n' "$dir"
    exit 3 ;;
  *)
    echo "Unknown subcommand: $mode" >&2; exit 2 ;;
esac
"""


@pytest.fixture()
def wizard_stub(tmp_path, monkeypatch):
    """A fake contract-capable eco-wizard binary + clean caches/env."""
    stub = tmp_path / "eco-wizard-stub"
    stub.write_text(_STUB, encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    ez._capability_cache.clear()
    monkeypatch.setenv("ECO_WIZARD", str(stub))
    monkeypatch.delenv("ECO_WIZARD_PREFIX", raising=False)
    monkeypatch.setenv("ECO_FRAMEWORK", str(tmp_path / "framework"))
    (tmp_path / "framework").mkdir()
    return stub


def test_capabilities_probe_parses_version_json(wizard_stub, tmp_path):
    caps = _wizard_capabilities(str(wizard_stub), [])
    assert caps is not None
    assert caps["version"] == "0.2.0-stub"
    assert {"json-output", "manifest-v1"} <= caps["capabilities"]
    # Cached: second call hits the TTL cache.
    assert _wizard_capabilities(str(wizard_stub), []) is caps


def test_new_json_manifest_reports_nested_layout(wizard_stub, tmp_path):
    res = _run_wizard(
        _WizardArgs(name="Eco.Wrap", project_type="APP", language="C", out_dir="."),
        tmp_path,
    )
    assert not res.is_error
    assert "eco_wizard created Eco.Wrap (C/APP)" in res.content
    # v0.1.3+ nests: project_dir '<Name>/' and paths rebased onto project_dir.
    assert res.details["entry_file"] == "Eco.Wrap/SourceFiles/EcoWrap.c"
    assert (
        res.details["build_subdir"]
        == "Eco.Wrap/AssemblyFiles/Linux/gcc_v132"
    )
    assert "run_build project_subdir: 'Eco.Wrap/AssemblyFiles/Linux/gcc_v132'" in res.content
    assert res.details["manifest"]["status"] == "created"
    assert res.details["wizard_version"] == "0.2.0-stub"
    # --verify is passed by default (explicit build dry-run request).
    assert res.details["manifest"]["validation"]["build_dry_run"] is True


def test_new_json_error_contract_surfaces_code_and_hint(wizard_stub, tmp_path, monkeypatch):
    monkeypatch.setenv("ECO_STUB_PRE_CREATED", "1")
    (tmp_path / "Eco.Wrap").mkdir()
    res = _run_wizard(
        _WizardArgs(name="Eco.Wrap", project_type="APP", language="C", out_dir="."),
        tmp_path,
    )
    assert res.is_error
    assert "POLICY_EXISTS" in res.content
    assert "rc=5" in res.content and "policy-denied" in res.content
    assert "hint: Use --if-absent." in res.content
    assert res.details["exit_code"] == 5


def test_if_absent_rerun_reports_reused(wizard_stub, tmp_path):
    first = _run_wizard(
        _WizardArgs(name="Eco.Re", project_type="APP", language="C", out_dir="."),
        tmp_path,
    )
    assert first.details["manifest"]["status"] == "created"
    again = _run_wizard(
        _WizardArgs(
            name="Eco.Re",
            project_type="APP",
            language="C",
            out_dir=".",
            if_absent=True,
        ),
        tmp_path,
    )
    assert not again.is_error
    assert again.details["manifest"]["status"] == "reused"
    assert "status \"reused\"" in again.content or "reused" in again.content


def test_wrapper_rejects_non_c_languages_up_front(wizard_stub, tmp_path):
    res = _run_wizard(
        _WizardArgs(name="Eco.Py", language="Python", out_dir="."),
        tmp_path,
    )
    assert res.is_error
    assert "does not support language 'Python'" in res.content


def test_wrapper_prechecks_eco_framework(wizard_stub, tmp_path, monkeypatch):
    monkeypatch.delenv("ECO_FRAMEWORK", raising=False)
    res = _run_wizard(
        _WizardArgs(name="Eco.NE", project_type="APP", language="C", out_dir="."),
        tmp_path,
    )
    assert res.is_error
    assert "ECO_FRAMEWORK" in res.content


def test_dry_run_reports_planned_tree(wizard_stub, tmp_path):
    res = _run_wizard(
        _WizardArgs(
            name="Eco.Dry",
            project_type="APP",
            language="C",
            out_dir=".",
            dry_run=True,
        ),
        tmp_path,
    )
    assert not res.is_error
    assert res.details["manifest"]["status"] == "created"  # stub echoes created
    assert "DRY-RUN: nothing was written" in res.content


def test_rc0_without_manifest_is_not_retried(wizard_stub, tmp_path, monkeypatch):
    monkeypatch.setenv("ECO_STUB_BAD_JSON", "1")
    res = _run_wizard(
        _WizardArgs(name="Eco.BadManifest", project_type="APP", language="C", out_dir="."),
        tmp_path,
    )
    assert res.is_error
    assert "not retried" in res.content
    assert (tmp_path / "Eco.BadManifest").is_dir()
    assert not (tmp_path / "SourceFiles").exists()


def test_legacy_rejects_json_only_arguments(wizard_stub, tmp_path, monkeypatch):
    monkeypatch.setenv("ECO_STUB_LEGACY", "1")
    res = _run_wizard(
        _WizardArgs(
            name="Eco.LegacyDry",
            project_type="APP",
            language="C",
            out_dir=".",
            dry_run=True,
        ),
        tmp_path,
    )
    assert res.is_error
    assert "dry_run" in res.content
    assert not (tmp_path / "SourceFiles").exists()


def test_validate_tool_ok_and_broken(wizard_stub, tmp_path):
    _run_wizard(
        _WizardArgs(name="Eco.Val", project_type="APP", language="C", out_dir="."),
        tmp_path,
    )
    ok = _run_validate(_ValidateArgs(path="Eco.Val"), tmp_path)
    assert not ok.is_error
    assert "passes the scaffold checks" in ok.content
    # Break the scaffold: SourceFiles/ gone → rc 3 + error findings.
    import shutil

    shutil.rmtree(tmp_path / "Eco.Val" / "SourceFiles")
    broken = _run_validate(_ValidateArgs(path="Eco.Val"), tmp_path)
    assert broken.is_error
    assert "MISSING_ENTRY" in broken.content
    assert "[warn] MISSING_WORKSPACE" in broken.content


def test_validate_rc0_without_schema_is_an_error(wizard_stub, tmp_path, monkeypatch):
    monkeypatch.setenv("ECO_STUB_BAD_VALIDATE", "1")
    broken = _run_validate(_ValidateArgs(path="."), tmp_path)
    assert broken.is_error
    assert "no parseable JSON" not in broken.content


def test_legacy_fallback_without_json_capability(wizard_stub, tmp_path, monkeypatch):
    # Legacy binaries: no `version --json`, text-mode `new` scaffolds into
    # out_dir directly (no nested <Name>/).
    monkeypatch.setenv("ECO_STUB_LEGACY", "1")
    res = _run_wizard(
        _WizardArgs(name="Eco.Old", project_type="APP", language="C", out_dir="."),
        tmp_path,
    )
    assert not res.is_error
    assert "legacy wizard" in res.content
    assert "out_dir: '.'" in res.content
    assert res.details["entry_file"] == "SourceFiles/EcoOld.c"
    assert res.details["build_subdir"] is None or isinstance(
        res.details["build_subdir"],
        (str, type(None)),
    )


def test_wizard_and_validate_not_resolved_leads_to_actionable_error(tmp_path, monkeypatch):
    monkeypatch.delenv("ECO_WIZARD", raising=False)
    monkeypatch.delenv("ECO_WIZARD_PATH", raising=False)
    monkeypatch.setattr(ez, "_resolve_wizard", lambda: None)
    res = _run_wizard(
        _WizardArgs(name="Eco.X", project_type="APP", language="C", out_dir="."),
        tmp_path,
    )
    assert res.is_error
    assert "executable was not found" in res.content
    vres = _run_validate(_ValidateArgs(path="."), tmp_path)
    assert vres.is_error
