"""Content-addressed storage (Phase 7)."""

from __future__ import annotations

from sec_edgar.storage import LocalStorage, content_sha1, store_content


def test_local_storage_roundtrip(tmp_path):
    storage = LocalStorage(tmp_path)
    key = store_content(b"hello world", prefix="raw", storage=storage)
    assert key == f"raw/{content_sha1(b'hello world')}"
    assert storage.exists(key)
    assert storage.get_bytes(key) == b"hello world"


def test_identical_bytes_dedupe(tmp_path):
    storage = LocalStorage(tmp_path)
    k1 = store_content(b"same payload", prefix="text", storage=storage)
    k2 = store_content(b"same payload", prefix="text", storage=storage)
    assert k1 == k2
    # Stored exactly once.
    files = list((tmp_path / "text").iterdir())
    assert len(files) == 1


def test_different_bytes_distinct_keys(tmp_path):
    storage = LocalStorage(tmp_path)
    k1 = store_content(b"alpha", prefix="raw", storage=storage)
    k2 = store_content(b"beta", prefix="raw", storage=storage)
    assert k1 != k2
    assert len(list((tmp_path / "raw").iterdir())) == 2
