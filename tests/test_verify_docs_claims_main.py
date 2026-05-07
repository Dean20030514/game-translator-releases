#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Integration tests for ``scripts/verify_docs_claims.py`` main_fast_path.

r64 T1 fix: split from ``tests/test_verify_docs_claims.py`` (was 790 lines,
near the 800-line cap). Helper unit tests stay in ``test_verify_docs_claims.py``;
integration tests for ``main_fast_path`` + ``parse_claims`` edge cases +
workflow / execute_all_ci_test_steps regressions move here.
"""

from __future__ import annotations

import sys
import tempfile
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Helper (r64 T1 split): copied from tests/test_verify_docs_claims.py
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# main()  —  fast path exit-code matrix
# ---------------------------------------------------------------------------


def _make_fixture_repo(
    td: Path,
    *,
    ci_steps: int,
    test_files: int,
    tests_per_file: int = 1,
    self_test_assertion_steps: tuple[int, ...] = (),
    claim_ci: int | None = None,
    claim_test_files: int | None = None,
    claim_tests_total: int | None = None,
    claim_assertion_points: int | None = None,
    oversized_count: int = 0,
) -> None:
    """Build synthetic repo under ``td`` so ``main()`` runs via
    ``--repo-root``.  Levers map to the 4 drift dimensions; each
    ``claim_*`` defaults to the matching real value (drift only on
    explicit override).  ``tests_per_file`` × ``test_files`` controls
    AST tests_total; ``self_test_assertion_steps`` adds CI steps
    named ``Self-test FOO (N assertions)`` for assertion_points."""
    (td / ".github" / "workflows").mkdir(parents=True)
    (td / "tests").mkdir()
    (td / "scripts").mkdir()

    # tests/ — n synthetic test modules with K real def test_* each.
    for i in range(test_files):
        bodies = "\n\n".join(f"def test_{i}_{j}():\n    assert True" for j in range(tests_per_file))
        (td / "tests" / f"test_synthetic_{i}.py").write_text(bodies + "\n", encoding="utf-8")

    # .github/workflows/test.yml — n synthetic test steps + optional
    # self-test steps.  Total step count = ci_steps; the first
    # ``len(self_test_assertion_steps)`` are self-test, the rest are
    # plain ``Run *`` test steps so ``execute_all_ci_test_steps``
    # can find them.  Build by hand — yaml is column-sensitive and
    # textwrap.dedent's common-prefix logic mangles interpolated blocks.
    yaml_lines = [
        "name: Tests",
        "on: [push]",
        "jobs:",
        "  test:",
        "    runs-on: ubuntu-latest",
        "    steps:",
    ]
    self_steps = list(self_test_assertion_steps)
    plain_steps = ci_steps - len(self_steps)
    if plain_steps < 0:
        raise ValueError("ci_steps must be >= len(self_test_assertion_steps)")
    for k, n in enumerate(self_steps):
        yaml_lines.append(f"      - name: Self-test FOO_{k} ({n} assertions)")
        yaml_lines.append('        run: python -c "pass"')
    for i in range(plain_steps):
        yaml_lines.append(f"      - name: Run synthetic-{i}")
        yaml_lines.append('        run: python -c "pass"')
    (td / ".github" / "workflows" / "test.yml").write_text(
        "\n".join(yaml_lines) + "\n",
        encoding="utf-8",
    )

    # HANDOFF.md — fenced block with the *claimed* numbers.  When a
    # specific claim is None, default it to the real value so that
    # only the lever explicitly varied by the caller drifts.
    real_tests_total = test_files * tests_per_file
    real_assertion_points = real_tests_total + sum(self_steps)
    if claim_ci is None:
        claim_ci = ci_steps
    if claim_test_files is None:
        claim_test_files = test_files
    if claim_tests_total is None:
        claim_tests_total = real_tests_total
    if claim_assertion_points is None:
        claim_assertion_points = real_assertion_points
    (td / "HANDOFF.md").write_text(
        textwrap.dedent(
            f"""\
            # HANDOFF

            <!-- VERIFIED-CLAIMS-START -->
            tests_total: {claim_tests_total}
            test_files: {claim_test_files}
            ci_steps: {claim_ci}
            assertion_points: {claim_assertion_points}
            <!-- VERIFIED-CLAIMS-END -->
            """
        ),
        encoding="utf-8",
    )

    # Synthetic oversized .py files at root (not under tests/ to keep
    # test_files count clean — find_oversized_py_files walks the
    # entire root, count_test_files only walks tests/).
    for i in range(oversized_count):
        (td / f"big_{i}.py").write_text("x\n" * 1000, encoding="utf-8")




def test_main_fast_path_returns_zero_when_everything_matches():
    """When file-size / test-file count / CI step count all match
    the fenced claims, ``main(['--fast', '--repo-root', td])`` exits
    0 and prints a success summary."""
    from scripts.verify_docs_claims import main

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _make_fixture_repo(td, ci_steps=5, test_files=3, claim_ci=5, claim_test_files=3)
        rc = main(["--fast", "--repo-root", str(td)])
    assert rc == 0, f"expected exit 0, got {rc}"
    print("[OK] main_fast_path_returns_zero_when_everything_matches")


def test_main_fast_path_fails_on_oversized_py_file():
    """Any ``.py`` over the 800-line limit makes ``--fast`` exit 1
    even if all other dimensions agree."""
    from scripts.verify_docs_claims import main

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _make_fixture_repo(
            td, ci_steps=5, test_files=3, claim_ci=5, claim_test_files=3, oversized_count=1
        )
        rc = main(["--fast", "--repo-root", str(td)])
    assert rc == 1, f"expected exit 1 on oversized .py, got {rc}"
    print("[OK] main_fast_path_fails_on_oversized_py_file")


def test_main_fast_path_fails_on_test_file_count_drift():
    """Real test_files (3) > claim (2) → drift → exit 1."""
    from scripts.verify_docs_claims import main

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _make_fixture_repo(td, ci_steps=5, test_files=3, claim_ci=5, claim_test_files=2)
        rc = main(["--fast", "--repo-root", str(td)])
    assert rc == 1, f"expected exit 1 on test-files drift, got {rc}"
    print("[OK] main_fast_path_fails_on_test_file_count_drift")


def test_main_fast_path_fails_on_ci_steps_drift():
    """Real ci_steps (5) > claim (4) → drift → exit 1."""
    from scripts.verify_docs_claims import main

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _make_fixture_repo(td, ci_steps=5, test_files=3, claim_ci=4, claim_test_files=3)
        rc = main(["--fast", "--repo-root", str(td)])
    assert rc == 1, f"expected exit 1 on ci-steps drift, got {rc}"
    print("[OK] main_fast_path_fails_on_ci_steps_drift")


def test_main_fast_path_fails_on_missing_handoff():
    """If HANDOFF.md is missing the claim block, exit 1 (setup
    error surfaces as failure — silent pass would defeat the
    drift detector)."""
    from scripts.verify_docs_claims import main

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _make_fixture_repo(td, ci_steps=5, test_files=3, claim_ci=5, claim_test_files=3)
        # Overwrite HANDOFF without claim block.
        (td / "HANDOFF.md").write_text("# HANDOFF\nno block.\n", encoding="utf-8")
        rc = main(["--fast", "--repo-root", str(td)])
    assert rc == 1, f"expected exit 1 on missing claim block, got {rc}"
    print("[OK] main_fast_path_fails_on_missing_handoff")


def test_main_fast_path_fails_on_tests_total_drift():
    """Round 49 contract update: ``tests_total`` is derived statically
    via AST (no subprocess), so ``--fast`` checks it just like the
    other three keys.  Real synthetic = 3 tests (3 files × 1 each),
    claim_tests_total = 99 → drift → exit 1."""
    from scripts.verify_docs_claims import main

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _make_fixture_repo(
            td, ci_steps=5, test_files=3, claim_tests_total=99
        )  # diverge only this lever
        rc = main(["--fast", "--repo-root", str(td)])
    assert rc == 1, f"expected exit 1 on tests_total drift, got {rc}"
    print("[OK] main_fast_path_fails_on_tests_total_drift")


def test_main_fast_path_fails_on_assertion_points_drift():
    """``assertion_points = tests_total + self-test (N assertions)``.
    Synthetic fixture: 2 self-test steps with 5 + 7 assertions and
    3 plain tests → real = 3 + 12 = 15.  Claim = 999 → drift."""
    from scripts.verify_docs_claims import main

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        _make_fixture_repo(
            td,
            ci_steps=5,
            test_files=3,
            self_test_assertion_steps=(5, 7),
            claim_assertion_points=999,
        )
        rc = main(["--fast", "--repo-root", str(td)])
    assert rc == 1, f"expected exit 1 on assertion_points drift, got {rc}"
    print("[OK] main_fast_path_fails_on_assertion_points_drift")


# ---------------------------------------------------------------------------
# Real-repo smoke — pin the contract that ``--fast`` against the
# actual project tree currently exits 0.  This catches the case
# where someone lands a commit *without* updating HANDOFF claims.
# ---------------------------------------------------------------------------


def test_main_fast_path_zero_against_real_repo():
    """Cross-check: running ``--fast`` against the real repo (no
    --repo-root override) must exit 0 at HEAD.  This is the
    smoke that ``pre-commit`` will run on every commit."""
    from scripts.verify_docs_claims import main

    rc = main(["--fast"])
    assert rc == 0, (
        f"real-repo --fast must exit 0 at HEAD; got {rc}.  "
        "If this fails, HANDOFF.md VERIFIED-CLAIMS block disagrees "
        "with reality — fix the claims before committing."
    )
    print("[OK] main_fast_path_zero_against_real_repo")


def test_parse_claims_skips_malformed_lines_silently_for_all_edge_cases():
    """Round 50 C2 Coverage HIGH-1 + Correctness LOW-3: 5 malformed
    scenarios silently skipped (backward-compat fail-open)."""
    import tempfile
    from scripts.verify_docs_claims import parse_claims, CLAIM_BLOCK_START, CLAIM_BLOCK_END

    for label, bad in [
        ("non-int value", "tests_total: abc"),
        ("missing colon", "tests_total 488"),
        ("empty value", "tests_total: "),
        ("embedded colon", "tests_total: 488: extra"),
        ("trailing decimal (LOW-3 fix)", "tests_total: 419.5"),
    ]:
        with tempfile.TemporaryDirectory() as td:
            h = Path(td) / "HANDOFF.md"
            h.write_text(
                f"{CLAIM_BLOCK_START}\n{bad}\nci_steps: 36\n{CLAIM_BLOCK_END}\n", encoding="utf-8"
            )
            claims = parse_claims(h)
        assert claims == {"ci_steps": 36}, f"{label}: {claims!r}"
    print("[OK] parse_claims_skips_malformed_lines_silently_for_all_edge_cases")


def test_parse_claims_returns_partial_dict_on_mixed_valid_invalid():
    """Round 50 1d: valid + unknown keys both kept (main reports MISS for required absent)."""
    import tempfile
    from scripts.verify_docs_claims import parse_claims, CLAIM_BLOCK_START, CLAIM_BLOCK_END

    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / "HANDOFF.md"
        h.write_text(
            f"{CLAIM_BLOCK_START}\ntests_total: 488\nunknown_key: 999\nci_steps: 36\n{CLAIM_BLOCK_END}\n",
            encoding="utf-8",
        )
        claims = parse_claims(h)
    assert claims == {"tests_total": 488, "unknown_key": 999, "ci_steps": 36}, f"got {claims!r}"
    print("[OK] parse_claims_returns_partial_dict_on_mixed_valid_invalid")


def test_workflow_includes_mock_target_consistency_check_step():
    """Round 50 1a + C4 deep-audit Security MEDIUM fix: CI step
    catches both mock.patch + patch.object forms; filter 'file_safety'
    (not 'core\\.file_safety') to handle qualified forms."""
    import yaml

    wp = REPO_ROOT / ".github" / "workflows" / "test.yml"
    steps = yaml.safe_load(wp.read_text(encoding="utf-8"))["jobs"]["test"]["steps"]
    matches = [s for s in steps if "Mock target consistency" in s.get("name", "")]
    assert len(matches) == 1, f"must have 1 such step; got {len(matches)}"
    run = matches[0].get("run", "")
    assert "mock\\.patch.*os\\.fstat" in run, "must catch mock.patch form"
    assert "patch\\.object" in run and "fstat" in run, "must catch patch.object form"
    assert 'grep -v "file_safety"' in run, "filter must be 'file_safety' (r50 C4 fix)"
    assert 'grep -v "core\\.file_safety"' not in run, (
        "filter must NOT be 'core\\.file_safety' — false-positives on qualified forms"
    )
    print("[OK] workflow_includes_mock_target_consistency_check_step")


def test_execute_all_ci_test_steps_skips_verify_docs_claims_full_self_step():
    """Round 49 C7 audit-tail: ``execute_all_ci_test_steps`` MUST skip
    CI steps invoking ``verify_docs_claims --full`` to prevent self-
    recursion (Windows WinError 32 file lock).  Pin the guard."""
    import tempfile
    from pathlib import Path
    from scripts.verify_docs_claims import execute_all_ci_test_steps

    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "workflow.yml"
        # Two steps: a benign echo + the self-recursive --full call.
        # If the skip is missing, the second step will fork python
        # which will fail to find scripts/verify_docs_claims.py in
        # the empty tempdir and raise RuntimeError; with the skip,
        # only the echo runs and the function returns cleanly.
        ws.write_text(
            "name: test\n"
            "on: push\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - name: Run echo test\n"
            "        run: echo passed\n"
            "      - name: Run verify_docs_claims --full self-gate\n"
            "        run: python scripts/verify_docs_claims.py --full\n",
            encoding="utf-8",
        )
        # No exception expected = skip works; any RuntimeError from
        # the self-recursion path would propagate up.
        execute_all_ci_test_steps(ws, repo_root=Path(td))
    print("[OK] execute_all_ci_test_steps_skips_verify_docs_claims_full_self_step")


# ---------------------------------------------------------------------------
# Test registry + entry point
# ---------------------------------------------------------------------------


TESTS = [
    test_main_fast_path_returns_zero_when_everything_matches,
    test_main_fast_path_fails_on_oversized_py_file,
    test_main_fast_path_fails_on_test_file_count_drift,
    test_main_fast_path_fails_on_ci_steps_drift,
    test_main_fast_path_fails_on_missing_handoff,
    test_main_fast_path_fails_on_tests_total_drift,
    test_main_fast_path_fails_on_assertion_points_drift,
    test_main_fast_path_zero_against_real_repo,
    # Round 50 C2 Coverage HIGH-1 + Correctness LOW-3: 5 malformed scenarios
    test_parse_claims_skips_malformed_lines_silently_for_all_edge_cases,
    # Round 50 1d: parse_claims partial dict on mixed valid/unknown
    test_parse_claims_returns_partial_dict_on_mixed_valid_invalid,
    # Round 50 1a: mock target stale trap CLASS guard contract
    test_workflow_includes_mock_target_consistency_check_step,
    # Round 49 C7 audit-tail: self-recursion guard
    test_execute_all_ci_test_steps_skips_verify_docs_claims_full_self_step,
]


def run_all() -> int:
    for t in TESTS:
        t()
    return len(TESTS)


if __name__ == "__main__":
    n = run_all()
    print()
    print("=" * 40)
    print(f"ALL {n} VERIFY DOCS CLAIMS MAIN TESTS PASSED")
    print("=" * 40)
