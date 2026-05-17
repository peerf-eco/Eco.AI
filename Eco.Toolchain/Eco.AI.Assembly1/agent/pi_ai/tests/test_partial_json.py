"""Partial-JSON accumulator smoke tests."""
from __future__ import annotations

import pytest

from agent.pi_ai.utils.json_parse import parse_partial, parse_strict


def test_parse_partial_complete_json():
    assert parse_partial('{"a": 1}') == {"a": 1}


def test_parse_partial_incremental():
    # Incremental accumulation (simulating streaming tool-call args)
    chunks = ['{"a":', ' 1, "b":', ' "x"}']
    acc = ""
    for c in chunks:
        acc += c
        parse_partial(acc)  # must not raise
    # Final
    assert parse_partial(acc) == {"a": 1, "b": "x"}


def test_parse_partial_empty():
    assert parse_partial("") == {}
    assert parse_partial("   ") == {}


def test_parse_strict_complete():
    assert parse_strict('{"x": 42}') == {"x": 42}


def test_parse_strict_invalid_raises():
    with pytest.raises(ValueError):
        parse_strict('{not json')
