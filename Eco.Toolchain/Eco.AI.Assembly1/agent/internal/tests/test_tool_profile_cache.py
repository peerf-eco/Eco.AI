"""Smoke + regression tests for ``read_component_profile``.

Regression context (2026-08-24): ``_read_profile`` referenced
``resolved_root`` — a name that only exists inside the tool factory — when
building the contract card. The NameError fired only on the SUCCESS path
(profile found, parsed, has cid+versions+DEVKIT), so every real lookup
died with "NameError: name 'resolved_root' is not defined" while all
error paths worked and the suite had zero coverage of this tool.

These tests exercise the full success path against a fake cache tree that
mirrors the production layout (marketplace_cache/_profiles/<Name>.json +
<Name>/SharedFiles/*.h), plus each failure branch.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.internal.tools.profile_cache import make_read_component_profile_tool


CID = "61C988E21B7041378C5BDAFBB68A3FA0"

IECO_HEADER = """\
#pragma once
/* Real headers declare `IID_IEcoMathC89 = {...}` (see _RE_IID in
   profile_cache.py, which requires the '=' after the name). */
static const GUID IID_IEcoMathC89 = \\
    {0x8b5c1e2a, 0x3f41, 0x4a55, {0x9c,0x2d,0x71,0xe0,0x44,0xa1,0xbb,0x03}};

typedef struct IEcoMathC89VTbl {
    double (ECOCALLMETHOD *add)(void* me, double a, double b);
    double (ECOCALLMETHOD *sqrt)(void* me, double x);
} IEcoMathC89VTbl;
"""

ID_HEADER = """\
#pragma once
ECOCALLMETHOD IEcoMathC89Ptr_t GetIEcoComponentFactoryPtr_""" + CID + """(uint16_t *sys);
"""


@pytest.fixture
def cache_root(tmp_path: Path) -> Path:
    """Fake marketplace_cache mirroring the production layout."""
    root = tmp_path / "marketplace_cache"
    profiles = root / "_profiles"
    profiles.mkdir(parents=True)
    shared = root / "Eco.Math.C89" / "SharedFiles"
    shared.mkdir(parents=True)
    (shared / "IEcoMathC89.h").write_text(IECO_HEADER, encoding="utf-8")
    (shared / "IdEcoMathC89.h").write_text(ID_HEADER, encoding="utf-8")

    # Real profiles carry a UTF-8 BOM (written by fetch_marketplace.py);
    # replicate that so the utf-8-sig read path is exercised.
    profile = {
        "id": "math-c89",
        "name": "Eco.Math.C89",
        "cid": CID,
        "versions": [
            {"name": "1.0.0.0", "files": [
                {"fileId": "fid-old", "contentType": "DEVKIT"},
            ]},
            {"name": "1.0.1.2", "files": [
                {"fileId": "fid-dyn-001", "contentType": "DYNAMICLIB"},
                {"fileId": "fid-devkit-002", "contentType": "DEVKIT"},
            ]},
        ],
    }
    raw = json.dumps(profile).encode("utf-8")
    (profiles / "Eco.Math.C89.json").write_bytes(b"\xef\xbb\xbf" + raw)

    # A second component so the missing-profile hint can list it.
    (profiles / "Eco.Other1.json").write_text(
        json.dumps({"cid": "X", "versions": []}), encoding="utf-8",
    )
    return root


def _tool(cache_root: Path):
    return make_read_component_profile_tool(cache_root=cache_root)


def test_success_returns_card_and_details(cache_root):
    """THE regression test: success path must not raise NameError and must
    include cid/version/devkit_file_id plus the SharedFiles contract card."""
    tool = _tool(cache_root)
    args = tool.args_schema(name="Eco.Math.C89")
    result = tool.execute(args)

    assert result.is_error is False
    body = result.content
    assert f"`{CID}`" in body                       # cid
    assert "`1.0.1.2`" in body                      # latest version ([-1])
    assert "`fid-devkit-002`" in body               # DEVKIT entry, not DYNAMICLIB
    # Contract card built from SharedFiles/
    assert "IID_IEcoMathC89" in body                # IID scan
    assert f"GetIEcoComponentFactoryPtr_{CID}" in body or \
        f"GetIEcoComponentFactoryPtr_{CID.lower()}" in body.lower()
    assert "IEcoMathC89.h vtable" in body
    assert "add" in body and "sqrt" in body         # vtable method scan
    assert "IEcoMathC89.h, IdEcoMathC89.h" in body  # layout listing
    details = result.details
    assert details == {
        "name": "Eco.Math.C89",
        "cid": CID,
        "version": "1.0.1.2",
        "devkit_file_id": "fid-devkit-002",
    }


def test_missing_profile_hints_available_names(cache_root):
    tool = _tool(cache_root)
    args = tool.args_schema(name="Eco.Typo.C89")
    result = tool.execute(args)
    assert result.is_error is True
    assert "no cached profile" in result.content
    assert "Eco.Math.C89, Eco.Other1" in result.content


def test_invalid_json_profile_reports_error(cache_root):
    (cache_root / "_profiles" / "Eco.Broken.json").write_text("{not json", encoding="utf-8")
    tool = _tool(cache_root)
    result = tool.execute(tool.args_schema(name="Eco.Broken"))
    assert result.is_error is True
    assert "not valid JSON" in result.content


def test_latest_version_without_devkit_is_reported(cache_root):
    p = cache_root / "_profiles" / "Eco.NoDevKit.json"
    p.write_text(json.dumps({
        "cid": "NODEVKIT01",
        "versions": [{"name": "2.0", "files": [
            {"fileId": "dyn-only", "contentType": "DYNAMICLIB"},
        ]}],
    }), encoding="utf-8")
    tool = _tool(cache_root)
    result = tool.execute(tool.args_schema(name="Eco.NoDevKit"))
    assert result.is_error is True
    assert "no DEVKIT file entry" in result.content
    assert "DYNAMICLIB" in result.content


def test_profile_without_cid_or_versions_is_error(cache_root):
    (cache_root / "_profiles" / "Eco.Empty.json").write_text("{}", encoding="utf-8")
    tool = _tool(cache_root)
    result = tool.execute(tool.args_schema(name="Eco.Empty"))
    assert result.is_error is True
    assert "no cid or no versions" in result.content
