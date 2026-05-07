#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Round 49 prevention: unit tests for ``scripts/verify_docs_claims.py``
— the multi-dimensional drift checker that breaks the r45-r48
"docs claim vs reality" cycle.  See ``scripts/verify_docs_claims.py``
docstring + r49 prelude commits (f3dee81 / 33687da) for full design
rationale.  Stdlib-only; no pytest dependency."""

from __future__ import annotations

import sys
import tempfile
import textwrap
from pathlib import Path

# Repo-root sys.path injection so ``scripts.verify_docs_claims`` is
# importable in the same way ``tests/test_*.py`` import ``core/`` etc.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# find_oversized_py_files
# ---------------------------------------------------------------------------


def test_find_oversized_py_files_returns_empty_when_all_under_limit():
    """When every .py is < max_lines, the helper returns ``[]``."""
    from scripts.verify_docs_claims import find_oversized_py_files

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "a.py").write_text("x = 1\n" * 50, encoding="utf-8")
        (root / "b.py").write_text("y = 2\n" * 100, encoding="utf-8")
        result = find_oversized_py_files(root, max_lines=800)
    assert result == [], f"expected [], got {result}"
    print("[OK] find_oversized_py_files_returns_empty_when_all_under_limit")


def test_find_oversized_py_files_detects_file_over_limit():
    """File exceeding the limit appears in the result with its line count."""
    from scripts.verify_docs_claims import find_oversized_py_files

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        small = root / "small.py"
        big = root / "big.py"
        small.write_text("a\n" * 100, encoding="utf-8")
        big.write_text("b\n" * 850, encoding="utf-8")
        result = find_oversized_py_files(root, max_lines=800)
    assert len(result) == 1, f"expected 1 oversized, got {len(result)}: {result}"
    found_path, found_lines = result[0]
    assert found_path.name == "big.py", f"expected big.py, got {found_path}"
    assert found_lines == 850, f"expected 850 lines, got {found_lines}"
    print("[OK] find_oversized_py_files_detects_file_over_limit")


def test_find_oversized_py_files_ignores_default_path_parts():
    """``.git`` / ``_archive`` / ``__pycache__`` / ``output`` are skipped
    by default — these directories are not part of the active source
    tree and may legitimately contain large files."""
    from scripts.verify_docs_claims import find_oversized_py_files

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Active source — should be reported.
        (root / "src.py").write_text("x\n" * 1000, encoding="utf-8")
        # Each of these should be ignored.
        for sub in ("_archive", "__pycache__", "output"):
            d = root / sub
            d.mkdir()
            (d / "huge.py").write_text("y\n" * 1500, encoding="utf-8")
        # .git uses a deeper layout; emulate by nesting.
        gitdir = root / ".git" / "hooks"
        gitdir.mkdir(parents=True)
        (gitdir / "buried.py").write_text("z\n" * 2000, encoding="utf-8")

        result = find_oversized_py_files(root, max_lines=800)
    assert len(result) == 1, f"expected 1 oversized (only src.py), got {result}"
    assert result[0][0].name == "src.py"
    print("[OK] find_oversized_py_files_ignores_default_path_parts")


def test_find_oversized_py_files_at_exact_boundary():
    """Files at exactly ``max_lines`` are NOT reported — the contract
    is ``> max_lines`` not ``>=`` (matches the user-supplied awk
    pattern ``$1>800``).  Pins the inclusive-vs-exclusive choice."""
    from scripts.verify_docs_claims import find_oversized_py_files

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Exactly 800 lines (no trailing newline → 800 lines of text +
        # 0 final blank).  ``wc -l`` counts newlines, so 800 ``\n``
        # produces 800.  We write 800 ``\n`` here to match.
        (root / "exact.py").write_text("a\n" * 800, encoding="utf-8")
        (root / "over.py").write_text("a\n" * 801, encoding="utf-8")
        result = find_oversized_py_files(root, max_lines=800)
    names = sorted(p.name for p, _ in result)
    assert names == ["over.py"], f"expected [over.py] only, got {names}"
    print("[OK] find_oversized_py_files_at_exact_boundary")


# ---------------------------------------------------------------------------
# count_test_files
# ---------------------------------------------------------------------------


def test_count_test_files_counts_test_prefix_and_smoke():
    """``count_test_files`` returns count of ``test_*.py`` plus
    ``smoke_test.py`` (legacy filename in this project that does not
    match ``test_*`` prefix but is part of the CI suite)."""
    from scripts.verify_docs_claims import count_test_files

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "test_foo.py").write_text("", encoding="utf-8")
        (root / "test_bar.py").write_text("", encoding="utf-8")
        (root / "smoke_test.py").write_text("", encoding="utf-8")
        # Should NOT be counted:
        (root / "helper.py").write_text("", encoding="utf-8")
        (root / "fixtures").mkdir()
        (root / "fixtures" / "test_data.py").write_text("", encoding="utf-8")
        n = count_test_files(root)
    assert n == 3, f"expected 3 (2 test_*.py + smoke_test.py), got {n}"
    print("[OK] count_test_files_counts_test_prefix_and_smoke")


def test_count_test_files_zero_when_dir_empty():
    """Empty tests dir returns 0 (not an error)."""
    from scripts.verify_docs_claims import count_test_files

    with tempfile.TemporaryDirectory() as td:
        n = count_test_files(Path(td))
    assert n == 0, f"expected 0, got {n}"
    print("[OK] count_test_files_zero_when_dir_empty")


# ---------------------------------------------------------------------------
# count_test_functions_in_module / derive_tests_total
# ---------------------------------------------------------------------------


def test_count_test_functions_in_module_counts_top_level_test_defs():
    """AST count of ``def test_*`` at module level — covers the six
    test files in this project that use Chinese summary lines instead
    of ``ALL N PASSED`` (where the runtime parser would return 0)."""
    from scripts.verify_docs_claims import count_test_functions_in_module

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test_x.py"
        p.write_text(
            "import os\n"
            "\n"
            "def test_alpha():\n"
            "    assert True\n"
            "\n"
            "def test_beta():\n"
            "    assert True\n"
            "\n"
            "def helper_fn():\n"  # NOT counted (no test_ prefix)
            "    pass\n"
            "\n"
            "async def test_async():\n"
            "    assert True\n"
            "\n"
            "class TestX:\n"  # method-level not counted (top-level only)
            "    def test_method(self):\n"
            "        pass\n",
            encoding="utf-8",
        )
        n = count_test_functions_in_module(p)
    assert n == 3, f"expected 3 (alpha + beta + async), got {n}"
    print("[OK] count_test_functions_in_module_counts_top_level_test_defs")


def test_count_test_functions_in_module_returns_zero_on_syntax_error():
    """Malformed Python returns 0 instead of crashing — fail-open
    keeps the drift checker resilient to in-progress edits."""
    from scripts.verify_docs_claims import count_test_functions_in_module

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "test_broken.py"
        p.write_text("def test_x(:\n", encoding="utf-8")  # syntax error
        n = count_test_functions_in_module(p)
    assert n == 0, f"expected 0 on syntax error, got {n}"
    print("[OK] count_test_functions_in_module_returns_zero_on_syntax_error")


def test_derive_tests_total_sums_across_test_modules():
    """Sums ``count_test_functions_in_module`` across every
    ``test_*.py`` plus ``smoke_test.py``; ignores helpers / fixtures."""
    from scripts.verify_docs_claims import derive_tests_total

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "test_a.py").write_text(
            "def test_1():\n    pass\ndef test_2():\n    pass\n",
            encoding="utf-8",
        )
        (td / "test_b.py").write_text("def test_3():\n    pass\n", encoding="utf-8")
        (td / "smoke_test.py").write_text("def test_smoke():\n    pass\n", encoding="utf-8")
        # Helpers / fixtures should not contribute.
        (td / "helper.py").write_text("def test_helper():\n    pass\n", encoding="utf-8")
        (td / "fixtures").mkdir()
        (td / "fixtures" / "test_data.py").write_text(
            "def test_fixture():\n    pass\n", encoding="utf-8"
        )
        n = derive_tests_total(td)
    assert n == 4, f"expected 4 (test_a:2 + test_b:1 + smoke_test:1), got {n}"
    print("[OK] derive_tests_total_sums_across_test_modules")


# ---------------------------------------------------------------------------
# derive_self_test_assertions / derive_assertion_points
# ---------------------------------------------------------------------------


def test_derive_self_test_assertions_parses_step_name_suffix():
    """Sum ``(N assertions)`` suffix on steps with ``self-test`` (case-insensitive)."""
    from scripts.verify_docs_claims import derive_self_test_assertions

    with tempfile.TemporaryDirectory() as td:
        wf = Path(td) / "test.yml"
        wf.write_text(
            textwrap.dedent(
                """\
                name: Tests
                on: [push]
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    steps:
                      - name: Run foo (5 assertions)
                        run: echo foo
                      - name: tl_parser self-tests (75 assertions)
                        run: echo tl
                      - name: screen self-tests (51 assertions)
                        run: echo screen
                """
            ),
            encoding="utf-8",
        )
        n = derive_self_test_assertions(wf)
    assert n == 75 + 51, (
        f"expected 126 (75+51 from self-test rows; the 'Run foo' "
        f"row's '(5 assertions)' must NOT count because no 'self-test' "
        f"in its name), got {n}"
    )
    print("[OK] derive_self_test_assertions_parses_step_name_suffix")


def test_derive_assertion_points_sums_tests_and_self_tests():
    """``derive_assertion_points = tests_total + self-test (N)``."""
    from scripts.verify_docs_claims import derive_assertion_points

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "tests").mkdir()
        (td / ".github" / "workflows").mkdir(parents=True)
        # 3 def test_* across 2 modules.
        (td / "tests" / "test_a.py").write_text(
            "def test_1():\n    pass\ndef test_2():\n    pass\n", encoding="utf-8"
        )
        (td / "tests" / "test_b.py").write_text("def test_3():\n    pass\n", encoding="utf-8")
        # 2 self-test steps with 10 + 20 assertions.
        (td / ".github" / "workflows" / "test.yml").write_text(
            textwrap.dedent(
                """\
                name: Tests
                on: [push]
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    steps:
                      - name: foo self-test (10 assertions)
                        run: echo a
                      - name: bar self-tests (20 assertions)
                        run: echo b
                """
            ),
            encoding="utf-8",
        )
        n = derive_assertion_points(td / "tests", td / ".github" / "workflows" / "test.yml")
    assert n == 33, f"expected 33 (3 tests + 30 assertions), got {n}"
    print("[OK] derive_assertion_points_sums_tests_and_self_tests")


# ---------------------------------------------------------------------------
# count_ci_steps
# ---------------------------------------------------------------------------


def test_count_ci_steps_parses_named_and_anonymous_steps():
    """``count_ci_steps`` returns ``len(jobs.test.steps)`` (every entry counts)."""
    from scripts.verify_docs_claims import count_ci_steps

    with tempfile.TemporaryDirectory() as td:
        wf = Path(td) / "test.yml"
        wf.write_text(
            textwrap.dedent(
                """\
                name: Tests
                on: [push]
                jobs:
                  test:
                    runs-on: ubuntu-latest
                    steps:
                      - uses: actions/checkout@v4
                      - name: Step A
                        run: echo a
                      - name: Step B
                        run: echo b
                """
            ),
            encoding="utf-8",
        )
        n = count_ci_steps(wf)
    assert n == 3, f"expected 3 (1 uses + 2 named), got {n}"
    print("[OK] count_ci_steps_parses_named_and_anonymous_steps")


def test_count_ci_steps_raises_on_missing_test_job():
    """If the ``test`` job is missing the helper raises ``KeyError`` —
    callers handle this as a structural error (not a soft drift)."""
    from scripts.verify_docs_claims import count_ci_steps

    with tempfile.TemporaryDirectory() as td:
        wf = Path(td) / "test.yml"
        wf.write_text(
            "name: Tests\non: [push]\njobs:\n  build:\n    runs-on: x\n", encoding="utf-8"
        )
        try:
            count_ci_steps(wf)
        except KeyError:
            print("[OK] count_ci_steps_raises_on_missing_test_job")
            return
    raise AssertionError("expected KeyError when test job is missing")


# ---------------------------------------------------------------------------
# parse_claims  —  fenced VERIFIED-CLAIMS block
# ---------------------------------------------------------------------------


def test_parse_claims_reads_fenced_block():
    """Parse fenced VERIFIED-CLAIMS block: ``key: value`` per line, ints only."""
    from scripts.verify_docs_claims import parse_claims

    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / "HANDOFF.md"
        h.write_text(
            textwrap.dedent(
                """\
                # HANDOFF

                some preamble.

                <!-- VERIFIED-CLAIMS-START -->
                tests_total: 439
                test_files: 32
                ci_steps: 33
                assertion_points: 565   # tl_parser 75 + screen 51 + tests 439
                <!-- VERIFIED-CLAIMS-END -->

                more text below.
                """
            ),
            encoding="utf-8",
        )
        claims = parse_claims(h)
    assert claims == {
        "tests_total": 439,
        "test_files": 32,
        "ci_steps": 33,
        "assertion_points": 565,
    }, f"unexpected claims: {claims}"
    print("[OK] parse_claims_reads_fenced_block")


def test_parse_claims_raises_when_block_missing():
    """Missing fenced block raises ``ValueError`` (setup error, not drift)."""
    from scripts.verify_docs_claims import parse_claims

    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / "HANDOFF.md"
        h.write_text("# HANDOFF\nno fenced block here.\n", encoding="utf-8")
        try:
            parse_claims(h)
        except ValueError as e:
            assert "VERIFIED-CLAIMS" in str(e), f"error must mention block name, got: {e}"
            print("[OK] parse_claims_raises_when_block_missing")
            return
    raise AssertionError("expected ValueError when fenced block is missing")


def test_parse_claims_ignores_inline_comments():
    """``key: 33   # comment`` parses to int 33 (split on first ``#``)."""
    from scripts.verify_docs_claims import parse_claims

    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / "HANDOFF.md"
        h.write_text(
            textwrap.dedent(
                """\
                <!-- VERIFIED-CLAIMS-START -->
                ci_steps: 33  # 1 checkout + 32 named
                <!-- VERIFIED-CLAIMS-END -->
                """
            ),
            encoding="utf-8",
        )
        claims = parse_claims(h)
    assert claims == {"ci_steps": 33}, f"expected {{ci_steps:33}}, got {claims}"
    print("[OK] parse_claims_ignores_inline_comments")


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


TESTS = [
    test_find_oversized_py_files_returns_empty_when_all_under_limit,
    test_find_oversized_py_files_detects_file_over_limit,
    test_find_oversized_py_files_ignores_default_path_parts,
    test_find_oversized_py_files_at_exact_boundary,
    test_count_test_files_counts_test_prefix_and_smoke,
    test_count_test_files_zero_when_dir_empty,
    test_count_test_functions_in_module_counts_top_level_test_defs,
    test_count_test_functions_in_module_returns_zero_on_syntax_error,
    test_derive_tests_total_sums_across_test_modules,
    test_derive_self_test_assertions_parses_step_name_suffix,
    test_derive_assertion_points_sums_tests_and_self_tests,
    test_count_ci_steps_parses_named_and_anonymous_steps,
    test_count_ci_steps_raises_on_missing_test_job,
    test_parse_claims_reads_fenced_block,
    test_parse_claims_raises_when_block_missing,
    test_parse_claims_ignores_inline_comments,
]


def run_all() -> int:
    """Run every helper unit test in registration order.

    r64 T1 split: integration / main_fast_path / parse_claims-edge /
    workflow / execute_all_ci tests moved to
    ``tests/test_verify_docs_claims_main.py`` (was 790 lines, near the
    800-line cap).
    """
    for t in TESTS:
        t()
    return len(TESTS)


if __name__ == "__main__":
    n = run_all()
    print()
    print("=" * 40)
    print(f"ALL {n} VERIFY DOCS CLAIMS HELPER TESTS PASSED")
    print("=" * 40)
