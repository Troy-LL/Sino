"""Safer hub bind and LAN token defaults.

Run from the worktree root:

    SINO_MODEL=stub .venv/bin/python brain/tests/test_auth_defaults.py
"""

import os
import sys
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

os.environ["SINO_MODEL"] = "stub"
os.environ.pop("SINO_MODE", None)
os.environ.pop("SINO_TOKEN", None)
os.environ.pop("ALLOW_OPEN", None)
os.environ.pop("ALLOW_CLEARTEXT", None)
os.environ.pop("HOST", None)
os.environ.pop("CERT", None)
os.environ.pop("KEY", None)

import server  # noqa: E402


def _clear_bind_env():
    for name in ("HOST", "SINO_TOKEN", "ALLOW_OPEN", "ALLOW_CLEARTEXT", "CERT", "KEY"):
        os.environ.pop(name, None)


def test_default_bind_is_localhost():
    _clear_bind_env()
    assert server.bind_host() == "127.0.0.1"
    assert server.validate_bind() == "127.0.0.1"


def test_lan_bind_without_token_exits():
    _clear_bind_env()
    os.environ["HOST"] = "0.0.0.0"
    try:
        server.validate_bind()
    except SystemExit as exc:
        assert "SINO_TOKEN" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_lan_bind_without_tls_exits():
    _clear_bind_env()
    os.environ["HOST"] = "0.0.0.0"
    os.environ["SINO_TOKEN"] = "secret"
    try:
        server.validate_bind()
    except SystemExit as exc:
        assert "CERT" in str(exc)
    else:
        raise AssertionError("expected SystemExit")


def test_lan_bind_allowed_with_token_and_cleartext_opt_in():
    _clear_bind_env()
    os.environ["HOST"] = "0.0.0.0"
    os.environ["SINO_TOKEN"] = "secret"
    os.environ["ALLOW_CLEARTEXT"] = "1"
    assert server.validate_bind() == "0.0.0.0"


def test_public_demo_opt_in():
    _clear_bind_env()
    os.environ["HOST"] = "0.0.0.0"
    os.environ["ALLOW_OPEN"] = "1"
    os.environ["ALLOW_CLEARTEXT"] = "1"
    assert server.validate_bind() == "0.0.0.0"


def test_token_optional_when_unset():
    _clear_bind_env()
    assert server.token_ok({}, {}, "192.168.1.8") is True


def test_loopback_skips_token():
    _clear_bind_env()
    os.environ["SINO_TOKEN"] = "secret"
    assert server.token_ok({}, {}, "127.0.0.1") is True
    assert server.token_ok({}, {}, "localhost") is True


def test_lan_client_needs_matching_token():
    _clear_bind_env()
    os.environ["SINO_TOKEN"] = "secret"
    assert server.token_ok({}, {}, "192.168.1.8") is False
    assert server.token_ok({"authorization": "Bearer secret"}, {}, "192.168.1.8") is True
    assert server.token_ok({"x-sino-token": "secret"}, {}, "192.168.1.8") is True
    assert server.token_ok({}, {"token": "secret"}, "192.168.1.8") is True
    assert server.token_ok({"authorization": "Bearer wrong"}, {}, "192.168.1.8") is False


def test_auth_paths():
    assert server.auth_needed_for_path("/listen") is True
    assert server.auth_needed_for_path("/questions") is True
    assert server.auth_needed_for_path("/health") is True
    assert server.auth_needed_for_path("/ws") is True
    assert server.auth_needed_for_path("/lola/") is False
    assert server.auth_needed_for_path("/") is False


def main():
    tests = [
        test_default_bind_is_localhost,
        test_lan_bind_without_token_exits,
        test_lan_bind_without_tls_exits,
        test_lan_bind_allowed_with_token_and_cleartext_opt_in,
        test_public_demo_opt_in,
        test_token_optional_when_unset,
        test_loopback_skips_token,
        test_lan_client_needs_matching_token,
        test_auth_paths,
    ]
    failed = 0
    for test in tests:
        _clear_bind_env()
        try:
            test()
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
        else:
            print(f"ok   {test.__name__}")
    _clear_bind_env()
    if failed:
        raise SystemExit(failed)


if __name__ == "__main__":
    main()
