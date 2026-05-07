#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for ``safety/file_safety.py`` (r48 Step 2 helper, r56 M2 moved).

Covers ``check_fstat_size`` 3 contract scenarios + 22 caller-integration
TOCTOU-growth-attack regressions across the 12 modules using the helper.
See r48 Step 3 audit / r49 expansion / r50 C4 filter relaxation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_check_fstat_size_within_limit():
    """Round 48 Step 2: file under the cap returns (True, real_size).

    Caller's downstream logic should proceed normally."""
    import tempfile
    from pathlib import Path
    from safety.file_safety import check_fstat_size

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "small.txt"
        p.write_bytes(b"hello world")  # 11 bytes
        with open(p, "rb") as f:
            ok, size = check_fstat_size(f, max_size=100)
        assert ok is True, f"11-byte file under 100-byte cap must return True, got ok={ok}"
        assert size == 11, f"observed_size must be 11 bytes, got {size}"
    print("[OK] check_fstat_size_within_limit")


def test_check_fstat_size_over_limit():
    """Round 48 Step 2: file at exactly cap+1 bytes returns (False,
    cap+1).  Smallest size that should be rejected — matches the
    ``size <= max_size`` (not ``<``) contract documented in
    ``check_fstat_size`` docstring."""
    import tempfile
    from pathlib import Path
    from safety.file_safety import check_fstat_size

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "big.txt"
        p.write_bytes(b"x" * 101)  # 101 bytes
        with open(p, "rb") as f:
            ok, size = check_fstat_size(f, max_size=100)
        assert ok is False, f"101-byte file over 100-byte cap must return False, got ok={ok}"
        assert size == 101, f"observed_size must be 101 bytes, got {size}"
    print("[OK] check_fstat_size_over_limit")


def test_check_fstat_size_at_cap_boundary():
    """Round 48 Step 2: file at exactly cap bytes returns (True, cap).
    Pins the ``size <= max_size`` boundary — exact match must pass.
    Mirrors the >/>= operator-pinning tests for csv_engine cap (r47
    G1 + r48 G1.1)."""
    import tempfile
    from pathlib import Path
    from safety.file_safety import check_fstat_size

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "exact.txt"
        p.write_bytes(b"x" * 100)  # exactly 100 bytes
        with open(p, "rb") as f:
            ok, size = check_fstat_size(f, max_size=100)
        assert ok is True, f"100-byte file at 100-byte cap must return True (<=); got ok={ok}"
        assert size == 100, f"observed_size must be 100 bytes, got {size}"
    print("[OK] check_fstat_size_at_cap_boundary")


def test_check_fstat_size_fail_open_on_oserror():
    """Round 48 Step 2: when os.fstat raises OSError (rare on a
    valid open fd), the helper returns (True, 0) — fail-open
    matching the design choice across r37-r47 path-based stat()
    callers.  Verified via mock injecting OSError into os.fstat."""
    import tempfile
    from pathlib import Path
    from unittest import mock
    from safety.file_safety import check_fstat_size

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "any.txt"
        p.write_bytes(b"any content")
        with open(p, "rb") as f:
            with mock.patch(
                "safety.file_safety.os.fstat", side_effect=OSError("simulated fstat failure")
            ):
                ok, size = check_fstat_size(f, max_size=100)
        assert ok is True, f"OSError fail-open: must return True so caller proceeds; got ok={ok}"
        assert size == 0, f"OSError fail-open: size must be 0, got {size}"
    print("[OK] check_fstat_size_fail_open_on_oserror")


def test_check_fstat_size_fail_open_on_valueerror():
    """Round 48 Step 3 audit-fix (Coverage M1 + Correctness LOW):
    when ``file_obj.fileno()`` raises ValueError (the contract for
    non-real-file objects like ``io.StringIO`` / ``io.BytesIO``),
    the helper must also return (True, 0) — fail-open with the same
    rationale as OSError.  Closes the round 48 audit's coverage gap
    where the helper was OSError-only and the contract was
    incomplete for arbitrary file-like wrappers."""
    import io
    from safety.file_safety import check_fstat_size

    # io.BytesIO has no real fd — calling fileno() raises
    # io.UnsupportedOperation, which inherits from ValueError.
    bio = io.BytesIO(b"not-a-real-file")
    ok, size = check_fstat_size(bio, max_size=100)
    assert ok is True, (
        f"ValueError fail-open (BytesIO has no fileno): must return "
        f"True so caller proceeds; got ok={ok}"
    )
    assert size == 0, f"ValueError fail-open: size must be 0, got {size}"

    # Same for StringIO.
    sio = io.StringIO("not-a-real-file")
    ok, size = check_fstat_size(sio, max_size=100)
    assert ok is True, (
        f"ValueError fail-open (StringIO has no fileno): must return True; got ok={ok}"
    )
    assert size == 0, f"ValueError fail-open: size must be 0, got {size}"

    print("[OK] check_fstat_size_fail_open_on_valueerror")


def run_all() -> int:
    """Run every helper unit test in this module.

    r64 T1 split: caller-integration tests moved to
    ``tests/test_file_safety_loaders.py``. This file keeps only the
    5 ``check_fstat_size`` helper unit tests.
    """
    tests = [
        test_check_fstat_size_within_limit,
        test_check_fstat_size_over_limit,
        test_check_fstat_size_at_cap_boundary,
        test_check_fstat_size_fail_open_on_oserror,
        test_check_fstat_size_fail_open_on_valueerror,
    ]
    for t in tests:
        t()
    return len(tests)


if __name__ == "__main__":
    n = run_all()
    print()
    print("=" * 40)
    print(f"ALL {n} FILE SAFETY HELPER TESTS PASSED")
    print("=" * 40)
