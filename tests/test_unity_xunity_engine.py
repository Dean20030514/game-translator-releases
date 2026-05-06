#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Round 55: ``engines.unity_xunity`` regression coverage.

Exercises the XUAT-format text engine added in r55:

  * ``detect()`` is manual-only (returns False)
  * ``extract_texts`` parses translation entries, regex rules, comments
    and blanks; ``=`` in original is split only on the first one
  * UTF-8 BOM round-trip preserved
  * Already-translated entries surface as status="translated" and are
    NOT re-emitted as pending
  * Regex rules ``r:"<pattern>"="<replacement>"`` extract the
    replacement for translation while keeping the pattern intact
  * ``write_back`` is byte-identical for everything except the lines
    that were actually translated (comments / blanks / line ordering /
    line endings / BOM all survive)
  * 50 MB OOM cap rejects oversized files

Pure standard library — no third-party dependencies.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engines.unity_xunity import UnityXUnityEngine, _parse_lines


# ────────────────────────────────────────────────────────────────────
# detect() / engine basics
# ────────────────────────────────────────────────────────────────────


def test_detect_is_manual_only():
    """detect() must always return False — XUAT files live in too many
    locations to auto-detect reliably."""
    engine = UnityXUnityEngine()
    with tempfile.TemporaryDirectory() as td:
        assert engine.detect(Path(td)) is False
    print("[OK] detect_is_manual_only")


def test_engine_profile_metadata():
    """Profile name + display name match the registry keys callers expect."""
    engine = UnityXUnityEngine()
    assert engine.profile.name == "unity_xunity"
    assert "XUnity" in engine.profile.display_name
    print("[OK] engine_profile_metadata")


# ────────────────────────────────────────────────────────────────────
# Parsing — line classification
# ────────────────────────────────────────────────────────────────────


def test_extract_basic_translation_entries():
    """Simple ``original=translation`` lines yield TranslatableUnits."""
    content = (
        "Hello=你好\n"
        "World=\n"           # pending
        "Goodbye=再见\n"
    )
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.txt"
        p.write_text(content, encoding="utf-8")
        engine = UnityXUnityEngine()
        units = engine.extract_texts(p)

    pending = [u for u in units if u.status == "pending"]
    assert len(pending) == 1, f"expected 1 pending, got {pending}"
    assert pending[0].original == "World"
    print("[OK] extract_basic_translation_entries")


def test_extract_preserves_already_translated_as_status():
    """Already-translated entries surface but are NOT re-emitted as pending.

    The engine returns only pending entries (the LLM has nothing to do
    with already-translated rows). Internal accounting still classifies
    them as "translated" for write_back fidelity.
    """
    content = "Hello=你好\nWorld=\n"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.txt"
        p.write_text(content, encoding="utf-8")
        engine = UnityXUnityEngine()
        units = engine.extract_texts(p)

    pending_originals = {u.original for u in units if u.status == "pending"}
    assert pending_originals == {"World"}
    # the already-translated "Hello=你好" should not be returned as pending
    assert all(u.original != "Hello" or u.status != "pending" for u in units)
    print("[OK] extract_preserves_already_translated_as_status")


def test_extract_skips_comments_and_blanks():
    """``//`` comments and blank lines never become TranslatableUnits."""
    content = (
        "// this is a comment\n"
        "\n"
        "RealEntry=\n"
        "// another comment\n"
        "\n"
    )
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.txt"
        p.write_text(content, encoding="utf-8")
        engine = UnityXUnityEngine()
        units = engine.extract_texts(p)

    pending = [u for u in units if u.status == "pending"]
    assert len(pending) == 1
    assert pending[0].original == "RealEntry"
    print("[OK] extract_skips_comments_and_blanks")


def test_extract_handles_equals_in_original():
    """``key=value=foo`` parses as original=``key`` translation=``value=foo``.

    Hard contract (Round 55): MUST use ``str.partition('=')`` (split
    first only). Switching to ``split('=')`` breaks payloads with
    ``=`` in original.
    """
    content = "key=value=foo\nplain=\n"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.txt"
        p.write_text(content, encoding="utf-8")
        engine = UnityXUnityEngine()
        units = engine.extract_texts(p)

    # "plain=" is the only pending; "key=value=foo" is already translated
    pending = [u for u in units if u.status == "pending"]
    assert len(pending) == 1
    assert pending[0].original == "plain"
    print("[OK] extract_handles_equals_in_original")


def test_extract_handles_utf8_bom():
    """A BOM-prefixed file parses correctly; no spurious leading char."""
    content = "BomKey=\nNormal=已译\n"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bom.txt"
        # Write with BOM
        p.write_bytes("﻿".encode("utf-8") + content.encode("utf-8"))
        engine = UnityXUnityEngine()
        units = engine.extract_texts(p)

    pending = [u for u in units if u.status == "pending"]
    assert len(pending) == 1
    assert pending[0].original == "BomKey", (
        f"BOM was not stripped — got {pending[0].original!r}"
    )
    print("[OK] extract_handles_utf8_bom")


def test_extract_skips_malformed_lines():
    """Lines without ``=`` and lines starting with ``=`` are skipped."""
    content = "no_equals_here\n=empty_original\nValid=\n"
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.txt"
        p.write_text(content, encoding="utf-8")
        engine = UnityXUnityEngine()
        units = engine.extract_texts(p)

    pending = [u for u in units if u.status == "pending"]
    assert len(pending) == 1
    assert pending[0].original == "Valid"
    print("[OK] extract_skips_malformed_lines")


# ────────────────────────────────────────────────────────────────────
# Regex rules (r:"...." = "....")
# ────────────────────────────────────────────────────────────────────


def test_extract_regex_rule_pending():
    """Regex rule with empty replacement → pending unit, pattern is metadata."""
    content = 'r:"Hello (\\d+)"=""\n'
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "rules.txt"
        p.write_text(content, encoding="utf-8")
        engine = UnityXUnityEngine()
        units = engine.extract_texts(p)

    pending = [u for u in units if u.status == "pending"]
    assert len(pending) == 1, f"expected 1 pending regex rule, got {len(pending)}"
    u = pending[0]
    assert u.metadata.get("line_type") == "regex_rule"
    assert u.metadata.get("regex_pattern") == "Hello (\\d+)"
    print("[OK] extract_regex_rule_pending")


def test_extract_regex_rule_already_filled():
    """Regex rule with non-empty replacement → translated unit, not pending."""
    content = 'r:"Hello (\\d+)"="你好 \\1"\n'
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "rules.txt"
        p.write_text(content, encoding="utf-8")
        engine = UnityXUnityEngine()
        units = engine.extract_texts(p)

    pending = [u for u in units if u.status == "pending"]
    assert len(pending) == 0
    print("[OK] extract_regex_rule_already_filled")


# ────────────────────────────────────────────────────────────────────
# write_back
# ────────────────────────────────────────────────────────────────────


def test_write_back_roundtrip_byte_identical_for_unchanged():
    """write_back preserves comments/blanks/order; only translated lines mutate."""
    content = (
        "// header comment\n"
        "\n"
        "Hello=你好\n"
        "World=\n"
        "// trailing comment\n"
    )
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        src = td_p / "x.txt"
        src.write_text(content, encoding="utf-8")
        out = td_p / "out"

        engine = UnityXUnityEngine()
        units = engine.extract_texts(src)
        # Translate "World"
        for u in units:
            if u.original == "World" and u.status == "pending":
                u.translation = "世界"
                u.status = "translated"

        written = engine.write_back(td_p, units, out)
        assert written == 1

        out_file = out / "x.txt"
        result = out_file.read_text(encoding="utf-8")

    expected = (
        "// header comment\n"
        "\n"
        "Hello=你好\n"
        "World=世界\n"
        "// trailing comment\n"
    )
    assert result == expected, f"round-trip failed:\nGOT:\n{result!r}\nWANT:\n{expected!r}"
    print("[OK] write_back_roundtrip_byte_identical_for_unchanged")


def test_write_back_preserves_bom():
    """If source has BOM, output has BOM. If not, no BOM is invented."""
    content = "Key=\n"
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        src = td_p / "bom.txt"
        src.write_bytes(b"\xef\xbb\xbf" + content.encode("utf-8"))
        out = td_p / "out"

        engine = UnityXUnityEngine()
        units = engine.extract_texts(src)
        for u in units:
            if u.status == "pending":
                u.translation = "键"
                u.status = "translated"

        engine.write_back(td_p, units, out)
        out_bytes = (out / "bom.txt").read_bytes()

    assert out_bytes.startswith(b"\xef\xbb\xbf"), "BOM lost on write-back"
    assert out_bytes[3:].decode("utf-8") == "Key=键\n"
    print("[OK] write_back_preserves_bom")


def test_write_back_regex_rule_preserves_pattern():
    """Regex-rule write-back: pattern verbatim, only replacement substituted.

    Hard contract (Round 55): pattern preserved verbatim, ONLY
    replacement translated.
    """
    content = 'r:"Hello (\\d+)"=""\n'
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        src = td_p / "rules.txt"
        src.write_text(content, encoding="utf-8")
        out = td_p / "out"

        engine = UnityXUnityEngine()
        units = engine.extract_texts(src)
        for u in units:
            if u.status == "pending":
                u.translation = "你好 \\1"
                u.status = "translated"

        engine.write_back(td_p, units, out)
        result = (out / "rules.txt").read_text(encoding="utf-8")

    assert result == 'r:"Hello (\\d+)"="你好 \\1"\n', (
        f"regex rule round-trip wrong: {result!r}"
    )
    print("[OK] write_back_regex_rule_preserves_pattern")


def test_write_back_preserves_crlf():
    """CRLF line endings in source survive write-back."""
    content = "// hdr\r\nHello=\r\n"
    with tempfile.TemporaryDirectory() as td:
        td_p = Path(td)
        src = td_p / "crlf.txt"
        src.write_bytes(content.encode("utf-8"))
        out = td_p / "out"

        engine = UnityXUnityEngine()
        units = engine.extract_texts(src)
        for u in units:
            if u.status == "pending":
                u.translation = "你好"
                u.status = "translated"

        engine.write_back(td_p, units, out)
        result = (out / "crlf.txt").read_bytes()

    assert result == b"// hdr\r\nHello=\xe4\xbd\xa0\xe5\xa5\xbd\r\n", (
        f"CRLF preservation broken: {result!r}"
    )
    print("[OK] write_back_preserves_crlf")


# ────────────────────────────────────────────────────────────────────
# OOM cap
# ────────────────────────────────────────────────────────────────────


def test_oom_cap_skips_oversized_file():
    """File > 50 MB cap is logged and skipped, not extracted."""
    # We can't realistically materialise 50 MB on disk in CI without
    # being slow. Patch the cap down to 1 KB and feed a 2 KB payload.
    from engines import unity_xunity as _mod
    original_cap = _mod._MAX_XUAT_FILE_SIZE
    _mod._MAX_XUAT_FILE_SIZE = 1024
    try:
        content = "Key=" + ("x" * 4096) + "\n"
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "big.txt"
            p.write_text(content, encoding="utf-8")
            engine = UnityXUnityEngine()
            units = engine.extract_texts(p)
        assert units == [], "oversized file must be skipped"
    finally:
        _mod._MAX_XUAT_FILE_SIZE = original_cap
    print("[OK] oom_cap_skips_oversized_file")


# ────────────────────────────────────────────────────────────────────
# Internal _parse_lines sanity
# ────────────────────────────────────────────────────────────────────


def test_parse_lines_classifies_all_types():
    """Internal _parse_lines covers blank/comment/translation/regex/malformed."""
    text = (
        "// comment\n"
        "\n"
        "key=value\n"
        'r:"pat"="rep"\n'
        "no_equals\n"
    )
    parsed = _parse_lines(text)
    assert len(parsed) == 5
    assert [p.line_type for p in parsed] == [
        "comment", "blank", "translation", "regex_rule", "malformed",
    ]
    assert parsed[2].original == "key" and parsed[2].translation == "value"
    assert parsed[3].regex_pattern == "pat" and parsed[3].translation == "rep"
    print("[OK] parse_lines_classifies_all_types")


# ────────────────────────────────────────────────────────────────────


def run_all() -> int:
    tests = [
        test_detect_is_manual_only,
        test_engine_profile_metadata,
        test_extract_basic_translation_entries,
        test_extract_preserves_already_translated_as_status,
        test_extract_skips_comments_and_blanks,
        test_extract_handles_equals_in_original,
        test_extract_handles_utf8_bom,
        test_extract_skips_malformed_lines,
        test_extract_regex_rule_pending,
        test_extract_regex_rule_already_filled,
        test_write_back_roundtrip_byte_identical_for_unchanged,
        test_write_back_preserves_bom,
        test_write_back_regex_rule_preserves_pattern,
        test_write_back_preserves_crlf,
        test_oom_cap_skips_oversized_file,
        test_parse_lines_classifies_all_types,
    ]
    for t in tests:
        t()
    return len(tests)


if __name__ == "__main__":
    n = run_all()
    print()
    print("=" * 40)
    print(f"ALL {n} XUAT TESTS PASSED")
    print("=" * 40)
