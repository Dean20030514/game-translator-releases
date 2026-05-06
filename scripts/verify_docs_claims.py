#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Round 49: cross-doc claim drift checker.

Breaks the r45-r48 "HANDOFF / CHANGELOG / CLAUDE / .cursorrules
all claim slightly different numbers because each round used the
*previous round's claim* as a baseline" cycle.  See
``_archive/CHANGELOG_RECENT_r50.md`` round 48 audit-tail for the
four drift incidents that motivated this tool (test count / file
count / CI step / line count) — each one was caught by the user running
independent ``find/wc/grep`` and noticing the docs disagreed
with reality.

Source-of-truth contract
------------------------

The fenced ``<!-- VERIFIED-CLAIMS-START -->...<!-- END -->`` block
in ``HANDOFF.md`` is the *only* place numbers are declared.  Every
other doc (``CLAUDE.md`` / ``.cursorrules`` / ``CHANGELOG.md`` /
``_archive/EVOLUTION.md`` / ``README.md`` / this file's docstring
even) references those declared numbers in
prose but does not re-declare them.  When the round-end docs sync
runs, only the fenced block needs updating; the prose around it
points the reader at "see VERIFIED-CLAIMS block".

Four checked dimensions
-----------------------

1. ``tests_total`` — sum of ``ALL N`` across every CI ``Run *`` step
   in ``.github/workflows/test.yml``.  Re-derived by ``--full`` only
   (running suites takes ~30-60s).  ``--fast`` skips this.
2. ``test_files`` — count of ``tests/test_*.py`` plus the legacy
   ``tests/smoke_test.py`` (which doesn't match the ``test_*.py``
   prefix but is part of the suite).  Cheap to derive.
3. ``ci_steps`` — ``len(jobs.test.steps)`` in the workflow yaml.
   Cheap.
4. ``assertion_points`` — ``tests_total + tl_parser self-tests +
   screen self-tests``.  The latter two are parsed from step names
   like ``Run tl_parser self-tests (75 assertions)``.  Re-derived
   by ``--full`` only.

Plus a fifth fail-fast guard:

5. **No .py file > 800 lines** — equivalent to the user-supplied
   ``find . -name "*.py" -not -path "./.git/*" -not -path
   "./_archive/*" | xargs wc -l | awk '$1>800 && $2!="total"'``
   one-liner, but in stdlib Python so it works the same on
   Windows / Linux / macOS without bash dependencies.

Usage
-----

::

    python scripts/verify_docs_claims.py            # equivalent to --fast
    python scripts/verify_docs_claims.py --fast     # explicit
    python scripts/verify_docs_claims.py --full     # CI / pre-push depth
    python scripts/verify_docs_claims.py --repo-root /tmp/fixture --fast

Exits 0 on no drift, 1 on any drift.  Prints a summary table
identifying which dimensions disagree.

Dependencies
------------

PyYAML for the workflow parse — same as ``scripts/verify_workflow.py``.
This is the project's only dev-tool exception to the zero-dependency
policy (production code stays stdlib-only; see CLAUDE.md).
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError:
    print(
        "[verify-docs-claims] ERROR: PyYAML not installed.  Install with:\n"
        "    pip install pyyaml --break-system-packages",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

REPO_ROOT_DEFAULT = Path(__file__).resolve().parent.parent
DEFAULT_MAX_LINES = 800
DEFAULT_IGNORE_PATH_PARTS = (".git", "_archive", "__pycache__", "output")
CLAIM_BLOCK_START = "<!-- VERIFIED-CLAIMS-START -->"
CLAIM_BLOCK_END = "<!-- VERIFIED-CLAIMS-END -->"

# All four canonical claim keys are derived statically (AST + yaml) so
# both ``--fast`` and ``--full`` can verify them without the 30-60s
# subprocess sweep.  ``--full`` additionally executes every CI test
# step as a passing-suite sanity check.
ALL_CLAIM_KEYS = ("tests_total", "test_files", "ci_steps", "assertion_points")


# ---------------------------------------------------------------------------
# Helpers — each returns a primitive that ``main`` can compare against
# the parsed claim dict.
# ---------------------------------------------------------------------------


def find_oversized_py_files(
    root: Path,
    max_lines: int = DEFAULT_MAX_LINES,
    ignore_path_parts: Iterable[str] = DEFAULT_IGNORE_PATH_PARTS,
) -> list[tuple[Path, int]]:
    """Walk ``root`` recursively, return ``(path, line_count)`` for
    every ``.py`` whose newline count strictly exceeds ``max_lines``.

    Path filtering matches the user-supplied awk one-liner: any
    component of the relative path equal to one of the ignore parts
    skips the file.  This lines up with ``find ... -not -path
    "./_archive/*"`` semantics.
    """
    ignore_set = set(ignore_path_parts)
    oversized: list[tuple[Path, int]] = []
    for py in root.rglob("*.py"):
        try:
            rel_parts = py.relative_to(root).parts
        except ValueError:
            rel_parts = py.parts
        if any(part in ignore_set for part in rel_parts):
            continue
        # Count newline bytes — equivalent to ``wc -l`` and avoids
        # decoding / list-building on large files.
        try:
            with open(py, "rb") as f:
                line_count = 0
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    line_count += chunk.count(b"\n")
        except OSError:
            continue
        if line_count > max_lines:
            oversized.append((py, line_count))
    return oversized


def _is_test_module(entry: Path) -> bool:
    """``test_*.py`` plus the legacy ``smoke_test.py`` (which doesn't
    use the standard prefix but is part of the suite)."""
    if not entry.is_file() or entry.suffix != ".py":
        return False
    name = entry.name
    return name.startswith("test_") or name == "smoke_test.py"


def count_test_files(tests_dir: Path) -> int:
    """Count test modules directly under ``tests_dir`` (non-recursive
    — fixtures / artifacts subdirs do not contribute to the suite
    count)."""
    if not tests_dir.is_dir():
        return 0
    return sum(1 for entry in tests_dir.iterdir() if _is_test_module(entry))


def count_test_functions_in_module(test_file: Path) -> int:
    """AST-count top-level ``def test_*`` (and ``async def test_*``)
    in ``test_file``.  This is the canonical per-file test count: it
    does not require running the file, handles every test-naming
    convention used in this project (``ALL N PASSED`` literal, Chinese
    ``=== 全部 X 测试通过 ===`` literal, no terminal print at all),
    and matches the way ``def test_*`` is registered in the per-file
    ``TESTS = [...]`` registries.

    Returns 0 on syntax error (the build hooks catch syntax errors
    via ``py_compile`` upstream — this fail-open keeps the drift
    checker resilient to in-progress edits)."""
    try:
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return 0
    n = 0
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                n += 1
    return n


def derive_tests_total(tests_dir: Path) -> int:
    """Sum ``count_test_functions_in_module`` across every test module
    in ``tests_dir``.  Pre-r49 this lived as a runtime ``ALL N``
    parser, but six suites in this project print Chinese summary
    lines (``=== 全部 X 测试通过 ===``) instead of ``ALL N PASSED``,
    so AST is the only universally-correct counter."""
    if not tests_dir.is_dir():
        return 0
    total = 0
    for entry in tests_dir.iterdir():
        if _is_test_module(entry):
            total += count_test_functions_in_module(entry)
    return total


def count_ci_steps(workflow_path: Path) -> int:
    """Parse the workflow yaml and return ``len(jobs.test.steps)``.

    Raises ``KeyError`` if the structure is missing required keys —
    callers should treat that as a structural error rather than a
    soft drift (the workflow is broken, not the claim).
    """
    with open(workflow_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    steps = doc["jobs"]["test"]["steps"]
    return len(steps)


_CLAIM_LINE_RE = re.compile(r"^\s*([a-z_]+)\s*:\s*(\d+)\s*(?:#.*)?\s*$")


def parse_claims(handoff_path: Path) -> dict[str, int]:
    """Return ``{key: int}`` parsed from the fenced
    ``VERIFIED-CLAIMS`` block in ``handoff_path``.

    Raises ``ValueError`` if the block is missing — without it the
    verifier has no source of truth to compare reality against, so
    callers must surface the absence as a setup failure.

    Inline comments after the value (``key: 33  # comment``) are
    tolerated by the regex, which only consumes leading whitespace,
    the key, the colon, and the int.
    """
    text = handoff_path.read_text(encoding="utf-8")
    start = text.find(CLAIM_BLOCK_START)
    end = text.find(CLAIM_BLOCK_END)
    if start < 0 or end < 0 or end <= start:
        raise ValueError(
            f"VERIFIED-CLAIMS block not found in {handoff_path}.  "
            f"Add the fenced block:\n"
            f"    {CLAIM_BLOCK_START}\n"
            f"    tests_total: <int>\n"
            f"    test_files: <int>\n"
            f"    ci_steps: <int>\n"
            f"    assertion_points: <int>\n"
            f"    {CLAIM_BLOCK_END}"
        )
    body = text[start + len(CLAIM_BLOCK_START) : end]
    claims: dict[str, int] = {}
    for line in body.splitlines():
        m = _CLAIM_LINE_RE.match(line)
        if m:
            claims[m.group(1)] = int(m.group(2))
    return claims


# ---------------------------------------------------------------------------
# Assertion point derivation — assertion_points = tests_total +
# self-test assertions parsed from CI step names.
# ---------------------------------------------------------------------------


_ASSERT_SUFFIX_RE = re.compile(r"\((\d+)\s+assertions?\)")


def derive_self_test_assertions(workflow_path: Path) -> int:
    """Sum the ``(N assertions)`` suffix on every CI step whose name
    contains ``self-test`` (case-insensitive).

    Used by ``derive_assertion_points`` to add the embedded-selftest
    contribution (currently ``tl_parser`` 75 + ``screen`` 51 = 126)
    to the AST-derived ``tests_total``.

    The convention pins the count to the step name itself, so adding
    a new assertion to the underlying module requires bumping the
    step name as well — that becomes the drift signal in CI."""
    with open(workflow_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    steps = doc["jobs"]["test"]["steps"]
    total = 0
    for step in steps:
        name = step.get("name", "")
        if "self-test" in name.lower():
            m = _ASSERT_SUFFIX_RE.search(name)
            if m:
                total += int(m.group(1))
    return total


def derive_assertion_points(tests_dir: Path, workflow_path: Path) -> int:
    """``tests_total + derive_self_test_assertions``."""
    return derive_tests_total(tests_dir) + derive_self_test_assertions(workflow_path)


# ---------------------------------------------------------------------------
# Full-mode runtime sanity check — execute every CI test step and
# fail if any returns non-zero.  Does NOT contribute to the count
# (counts are static); this is purely a "do the suites still pass?"
# gate, run in CI / pre-push.
# ---------------------------------------------------------------------------


def execute_all_ci_test_steps(workflow_path: Path, repo_root: Path) -> None:
    """Run every CI step whose ``name`` starts with ``Run `` (the
    project convention for test steps) and whose ``run`` is non-empty.

    Raises ``RuntimeError`` on the first failing step with the
    command and stderr tail attached.  No return value — the count
    of tests is derived statically by ``derive_tests_total``.

    Round 49 Step 3 (audit-fix Security HIGH) — ``shell=True`` trust
    contract:
        ``subprocess.run(run, shell=True)`` below executes commands
        sourced from ``.github/workflows/test.yml`` ``run:`` fields.
        This is **safe by construction** because that yaml is part of
        the repository and is reviewed via standard PR / branch-
        protection workflows alongside any other code change — i.e.
        it is *trusted configuration*, not user-supplied input.  The
        ``name:`` field is NOT interpolated into the executed command;
        only ``run:`` is, and ``run:`` is what the corresponding GHA
        runner would execute anyway.

        Threat model: a malicious PR that modifies ``run:`` to inject
        shellcode would equally affect the production CI run — there
        is no privilege boundary this verifier crosses that GHA does
        not.  ``shell=True`` is required because legitimate steps use
        compound shell syntax (e.g. ``python a.py && python b.py``);
        switching to ``shlex.split(run)`` would break those steps
        without adding a meaningful security boundary.

        DO NOT pass externally-sourced workflow yamls to this
        function (e.g. yamls fetched from untrusted forks at runtime).
        ``--full`` mode is intended for repository-local CI / pre-push
        runs only.  ``--fast`` mode (which this gating-tool defaults
        to in pre-commit) does NOT execute any CI steps and is safe
        regardless."""
    with open(workflow_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    steps = doc["jobs"]["test"]["steps"]

    for step in steps:
        name = step.get("name", "")
        run = step.get("run", "")
        if not run or not name.startswith("Run "):
            continue
        # Round 49 C7 audit-tail fix: skip the "Run verify_docs_claims
        # --full" step to prevent infinite self-recursion.  Without this
        # guard the --full mode invokes itself (CI yaml exposes the
        # --full gate as its own step), which recurses, holds the
        # output file lock, and eventually fails with WinError 32.
        # The current --full invocation already covers everything that
        # step would re-do — re-executing it adds no signal.
        #
        # Round 50 C2 audit-fix (Security LOW-4): match step NAME
        # explicitly instead of substring on `run` field.  Prior
        # substring match on `run` was brittle: it would also skip
        # ``echo verify_docs_claims --full`` (innocuous) or
        # ``python verify_docs_claims_extended.py --full`` (different
        # tool, should NOT skip).  Step names are stable repo-local
        # config reviewed via PR, so name match is safer + clearer.
        if name.startswith("Run verify_docs_claims --full"):
            continue
        proc = subprocess.run(
            run,
            shell=True,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"step failed (returncode={proc.returncode}):\n"
                f"  name: {name}\n"
                f"  cmd:  {run.strip()[:120]}\n"
                f"  stderr tail: {proc.stderr[-400:]}"
            )


# ---------------------------------------------------------------------------
# Round 52 C1: HANDOFF push-status drift check.  Catches the r51 trap
# where HANDOFF.md L29 declared "本地 main 含 r51 5 commits, 待用户手动
# push origin" but the user had already pushed afterwards — the prose
# went stale because no automation re-derived the unpushed-commit count.
# Same drift class as the r45-r48 cycle that motivated the rest of this
# tool, but on push state instead of test/file/CI counts.
# ---------------------------------------------------------------------------


# Match phrasings like:
#   "本地 main 含 r51 5 commits, 待用户手动 push origin"
#   "5 commits 待 push"
#   "X commits ... 待 push 至 origin"
# but NOT:
#   "7 commits 已全部 push 至 origin/main" (no 待 between commits and push)
#   "5 commits 已 push" (no 待)
# The 80/30 length caps prevent runaway cross-paragraph matches.
_PENDING_PUSH_RE = re.compile(r"(\d+)\s*commits?[\s\S]{0,80}?待[\s\S]{0,30}?push")


def parse_handoff_pending_push(handoff_text: str) -> int | None:
    """Extract the claimed unpushed-commit count from HANDOFF prose.

    Returns the integer captured by ``_PENDING_PUSH_RE`` on first match,
    or ``None`` if no "X commits ... 待 ... push" phrase is present.
    The returned value is the *claim* — pair with
    :func:`count_unpushed_commits` to detect drift.
    """
    m = _PENDING_PUSH_RE.search(handoff_text)
    if m is None:
        return None
    try:
        return int(m.group(1))
    except (ValueError, IndexError):
        return None


def count_unpushed_commits(repo_root: Path) -> int | None:
    """Return the real unpushed commit count via ``git rev-list``.

    ``None`` on any failure (git not on PATH, no remote, detached HEAD,
    fetch lag, parse error) — fail-open so this check never blocks a
    commit in a CI environment that may not have origin access.

    The check that consumes this value treats ``None`` as "skip the
    drift comparison"; only ``0`` (with claim > 0) is treated as drift.
    """
    try:
        proc = subprocess.run(
            ["git", "rev-list", "origin/main..HEAD", "--count"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    try:
        return int(proc.stdout.strip())
    except (ValueError, AttributeError):
        return None


def check_handoff_push_status(handoff_path: Path, repo_root: Path) -> str | None:
    """Return drift-issue string when HANDOFF claims pending push but
    git shows zero unpushed commits (= already pushed but doc not synced).

    Returns ``None`` (= no drift) when:
      - HANDOFF.md is unreadable (setup error, surfaced elsewhere)
      - HANDOFF makes no pending-push claim
      - git unavailable (CI fail-open)
      - real unpushed count matches the claim direction (claim > 0 and
        real > 0 — both agree there's pending work)

    Drift is asymmetric on purpose: only the "doc says pending, reality
    says pushed" direction is flagged, because the inverse ("doc silent,
    reality has unpushed commits") is the normal in-flight state during
    development.  A future maintainer can extend this with a
    ``min_count_threshold`` if needed.
    """
    try:
        text = handoff_path.read_text(encoding="utf-8")
    except OSError:
        return None
    claim = parse_handoff_pending_push(text)
    if claim is None:
        return None
    real = count_unpushed_commits(repo_root)
    if real is None:
        return None
    if claim > 0 and real == 0:
        return (
            f"HANDOFF.md claims {claim} commits pending push, but "
            f"`git rev-list origin/main..HEAD --count` returns 0 "
            f"(= already pushed). HANDOFF push-status section is stale — "
            f"sync it after every push, or remove the pending-push prose "
            f"once the push completes."
        )
    return None


# ---------------------------------------------------------------------------
# Reporter — formats a drift table for stdout.
# ---------------------------------------------------------------------------


def _format_row(key: str, real: int | None, claim: int | None) -> str:
    if real is None:
        real_s = "-"
        ok = "  N/A"
    elif claim is None:
        real_s = str(real)
        ok = "  MISS"
    elif real == claim:
        real_s = str(real)
        ok = "  OK"
    else:
        real_s = str(real)
        ok = "  DRIFT"
    claim_s = "-" if claim is None else str(claim)
    return f"  {key:<22} real={real_s:<8} claim={claim_s:<8} {ok}"


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="verify_docs_claims",
        description="Cross-doc claim drift checker (round 49).",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--fast",
        action="store_true",
        help="Fast checks only (file-size + test-files + ci-steps). Default.",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="Fast checks + execute every CI 'Run *' step as a passing-suite sanity gate.",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Override repo root (defaults to the parent of this script).",
    )
    p.add_argument(
        "--max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help=f"Soft limit per .py (default {DEFAULT_MAX_LINES}).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    full = args.full
    # ``--fast`` is the default when neither flag is given.
    repo_root = (args.repo_root or REPO_ROOT_DEFAULT).resolve()
    handoff_path = repo_root / "HANDOFF.md"
    workflow_path = repo_root / ".github" / "workflows" / "test.yml"
    tests_dir = repo_root / "tests"

    print("=" * 60)
    print(f"verify_docs_claims  ({'full' if full else 'fast'} mode)")
    print(f"  repo_root: {repo_root}")
    print("=" * 60)

    issues: list[str] = []

    # 1. claim block
    try:
        claims = parse_claims(handoff_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"\n[setup error] {e}", file=sys.stderr)
        return 1

    # 2. file-size
    oversized = find_oversized_py_files(repo_root, max_lines=args.max_lines)
    if oversized:
        issues.append(f"{len(oversized)} .py file(s) over {args.max_lines} lines:")
        for p, n in oversized:
            try:
                rel = p.relative_to(repo_root)
            except ValueError:
                rel = p
            issues.append(f"    {rel}  {n} lines")

    # 3-6. Derive all four canonical numbers statically.  Workflow yaml
    # is required for ci_steps + assertion_points; surface yaml parse
    # errors as setup failure rather than soft drift.
    real: dict[str, int] = {}
    try:
        real["test_files"] = count_test_files(tests_dir)
        real["ci_steps"] = count_ci_steps(workflow_path)
        real["tests_total"] = derive_tests_total(tests_dir)
        real["assertion_points"] = derive_assertion_points(tests_dir, workflow_path)
    except (FileNotFoundError, KeyError) as e:
        print(f"\n[setup error] workflow parse failed: {e}", file=sys.stderr)
        return 1

    # 7. (round 52 C1) HANDOFF push-status drift — claim of pending
    # commits while git shows zero unpushed = stale HANDOFF prose.
    # Fail-open on git unavailable; see :func:`check_handoff_push_status`.
    push_issue = check_handoff_push_status(handoff_path, repo_root)
    if push_issue:
        issues.append(push_issue)

    # 8. (--full only) execute every CI test step as a runtime sanity
    # gate.  Does NOT contribute to the count — counts are static.
    if full:
        try:
            execute_all_ci_test_steps(workflow_path, repo_root)
        except RuntimeError as e:
            print(f"\n[full mode] suite execution failed: {e}", file=sys.stderr)
            return 1

    # Drift comparison — print one row per claim key, then build the
    # issue list from any disagreement.
    print()
    for key in ALL_CLAIM_KEYS:
        print(_format_row(key, real.get(key), claims.get(key)))

    for key in ALL_CLAIM_KEYS:
        claim = claims.get(key)
        if claim is None:
            issues.append(f"claim missing: {key}")
        elif claim != real.get(key):
            issues.append(f"{key} drift: claim={claim} real={real.get(key)}")

    print()
    print("=" * 60)
    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"  - {issue}")
        print()
        print(
            "Fix HANDOFF.md VERIFIED-CLAIMS block to match reality, OR "
            "fix the underlying drift (e.g. split oversized files), then "
            "re-run.  Bypass at your own risk with `git commit --no-verify`."
        )
        return 1

    print("All claims match reality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
