#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTTP response-body size-cap regression tests for ``core/api_client.py``.

r64 T1 fix: split from ``tests/test_api_client.py`` (was 792 lines, near
the 800-line cap). Pure response-body-size-cap regressions (round 22 H1
+ round 53 monitor #2 W2 1-byte precision) move here.

Mock-target consistency contract preserved.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ============================================================
# Response-body size cap (round 22 — H1)
# ============================================================


def test_http_pool_rejects_oversized_response():
    """``HTTPSConnectionPool.post`` must stop reading once the response body
    exceeds ``MAX_API_RESPONSE_BYTES`` (32 MB) and raise ``ResponseTooLarge``.

    Guards against a malicious / misconfigured endpoint streaming unbounded
    data into the translator process, which would otherwise OOM.
    """
    from unittest.mock import patch, MagicMock
    from core.http_pool import HTTPSConnectionPool, ResponseTooLarge

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.getheaders = MagicMock(return_value=[])
    # Each read() returns 64 KB; the pool reads in 64 KB chunks so we hit the
    # 32 MB cap after ~513 iterations without needing to materialise 32 MB in
    # the test process.
    mock_resp.read = MagicMock(return_value=b"\x00" * 65536)

    mock_conn = MagicMock()
    mock_conn.getresponse = MagicMock(return_value=mock_resp)

    with patch("core.http_pool.http.client.HTTPSConnection", return_value=mock_conn):
        pool = HTTPSConnectionPool()
        try:
            pool.post("https://api.example.com/v1/x", b"{}", {})
            raised = False
        except ResponseTooLarge as e:
            raised = True
            msg = str(e)
            assert "32" in msg, f"expected size info in error msg, got: {msg}"
    assert raised, "expected ResponseTooLarge when pool reads past the cap"
    print("[OK] test_http_pool_rejects_oversized_response")


def test_w_monitor2_read_bounded_precision_at_cap():
    """Round 53 monitor #2: ``read_bounded`` precision deviation ≤ 1 byte.

    Pre-r53 baseline: each iteration read a full 64 KB chunk before the
    cap check fired, so streams could exceed the nominal cap by up to
    65535 bytes. r53 monitor #2 tightens this by sizing each read to
    ``min(_READ_CHUNK_SIZE, limit - total + 1)``; the +1 reserves one
    byte for overshoot detection but never accepts it. This test asserts
    the new precision contract.
    """
    from io import BytesIO
    from core.http_pool import read_bounded, ResponseTooLarge

    LIMIT = 1024  # 1 KB — small for fast test
    OVERSHOOT = 100  # data is limit + 100 bytes
    stream = BytesIO(b"\x00" * (LIMIT + OVERSHOOT))
    try:
        read_bounded(stream, limit=LIMIT)
    except ResponseTooLarge:
        pos = stream.tell()
        assert pos <= LIMIT + 1, (
            f"r53 monitor #2 precision contract violated: stream advanced "
            f"to position {pos} but cap is {LIMIT} (max deviation 1 byte)"
        )
        print(
            f"[OK] w_monitor2_read_bounded_precision_at_cap "
            f"(read {pos} bytes, limit {LIMIT}, deviation {pos - LIMIT})"
        )
        return
    raise AssertionError("expected ResponseTooLarge to raise")


def test_w_monitor2_read_bounded_at_exact_limit_succeeds():
    """``read_bounded`` returns full payload when size equals limit exactly."""
    from io import BytesIO
    from core.http_pool import read_bounded

    LIMIT = 2048
    payload = b"\xab" * LIMIT  # exactly at limit
    stream = BytesIO(payload)
    result = read_bounded(stream, limit=LIMIT)
    assert result == payload, "exact-limit payload must return intact"
    assert len(result) == LIMIT
    print("[OK] w_monitor2_read_bounded_at_exact_limit_succeeds")


def test_w_monitor2_read_bounded_one_byte_over_limit_raises():
    """Boundary: limit + 1 byte exactly triggers ResponseTooLarge."""
    from io import BytesIO
    from core.http_pool import read_bounded, ResponseTooLarge

    LIMIT = 2048
    stream = BytesIO(b"\xff" * (LIMIT + 1))
    try:
        read_bounded(stream, limit=LIMIT)
    except ResponseTooLarge:
        print("[OK] w_monitor2_read_bounded_one_byte_over_limit_raises")
        return
    raise AssertionError("limit + 1 byte must raise")


def test_api_client_urllib_rejects_oversized_response():
    """The urllib fallback path in ``APIClient`` must also enforce the cap —
    otherwise setting ``use_connection_pool=False`` would silently bypass
    the hardening.
    """
    from unittest.mock import patch, MagicMock
    from core import api_client
    from core.http_pool import ResponseTooLarge

    config = api_client.APIConfig(
        provider="xai",
        api_key="test",
        model="grok",
        max_retries=1,
        rpm=0,
        rps=0,
        use_connection_pool=False,
    )
    client = api_client.APIClient(config)

    mock_resp = MagicMock()
    mock_resp.read = MagicMock(return_value=b"\x00" * 65536)
    ctx = MagicMock()
    ctx.__enter__.return_value = mock_resp
    ctx.__exit__.return_value = False

    with patch.object(api_client.urlreq, "urlopen", return_value=ctx):
        try:
            client._call_api("sys", "user")
            raised = False
        except ResponseTooLarge:
            raised = True
    assert raised, "urllib fallback path should also raise ResponseTooLarge"
    print("[OK] test_api_client_urllib_rejects_oversized_response")


def run_all() -> int:
    """Run every response-body-cap test in this module."""
    tests = [
        test_http_pool_rejects_oversized_response,
        test_w_monitor2_read_bounded_precision_at_cap,
        test_w_monitor2_read_bounded_at_exact_limit_succeeds,
        test_w_monitor2_read_bounded_one_byte_over_limit_raises,
        test_api_client_urllib_rejects_oversized_response,
    ]
    for t in tests:
        t()
    return len(tests)


if __name__ == "__main__":
    n = run_all()
    print()
    print("=" * 40)
    print(f"ALL {n} API RESPONSE CAP TESTS PASSED")
    print("=" * 40)
