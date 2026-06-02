import hashlib
import io
import json
from urllib.error import URLError

import pytest

from src.business.update_manager import (
    UpdateDownloadError,
    UpdateManager,
    UpdateManifestError,
    UpdateNetworkError,
    is_newer_version,
    parse_semver,
    parse_update_manifest,
)


class FakeResponse:
    def __init__(self, data: bytes, headers=None):
        self._stream = io.BytesIO(data)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self, size=-1):
        return self._stream.read(size)


def _manifest(*, version="0.3.7", installer_hash=None):
    installer_hash = installer_hash or "b" * 64
    return {
        "schema": 1,
        "app": "MINGDA SignMaker",
        "version": version,
        "release_url": "https://github.com/example/repo/releases/tag/v0.3.7",
        "notes": "Release notes",
        "installer": {
            "url": "https://github.com/example/repo/releases/download/v0.3.7/MINGDA-SignMaker-Setup-0.3.7.exe",
            "sha256": installer_hash,
            "size_bytes": 456,
        },
    }


def test_parse_semver_accepts_v_prefix():
    assert parse_semver("v0.3.7") == (0, 3, 7)
    assert parse_semver("0.3.7") == (0, 3, 7)


def test_is_newer_version_handles_equal_and_lower_versions():
    assert is_newer_version("0.3.7", "0.3.6") is True
    assert is_newer_version("0.3.6", "0.3.6") is False
    assert is_newer_version("0.3.5", "0.3.6") is False


def test_parse_manifest_reads_single_installer():
    info = parse_update_manifest(_manifest(), current_version="0.3.6")

    assert info.version == "0.3.7"
    assert info.current_version == "0.3.6"
    assert info.asset.url.endswith("MINGDA-SignMaker-Setup-0.3.7.exe")
    assert info.asset.size_bytes == 456


def test_parse_manifest_rejects_missing_installer():
    manifest = _manifest()
    del manifest["installer"]

    with pytest.raises(UpdateManifestError, match="installer"):
        parse_update_manifest(manifest, current_version="0.3.6")


def test_check_for_update_returns_none_for_current_version(tmp_path):
    payload = json.dumps(_manifest(version="0.3.6")).encode("utf-8")

    def opener(_request, timeout):
        return FakeResponse(payload)

    manager = UpdateManager(
        current_version="0.3.6",
        cache_dir=tmp_path,
        manifest_url="https://example.test/signmaker-update.json",
        opener=opener,
    )

    assert manager.check_for_update() is None


def test_fetch_manifest_wraps_network_errors(tmp_path):
    def opener(_request, timeout):
        raise URLError("offline")

    manager = UpdateManager(
        current_version="0.3.6",
        cache_dir=tmp_path,
        manifest_url="https://example.test/signmaker-update.json",
        opener=opener,
    )

    with pytest.raises(UpdateNetworkError):
        manager.fetch_manifest()


def test_fetch_manifest_rejects_invalid_json(tmp_path):
    def opener(_request, timeout):
        return FakeResponse(b"{not json")

    manager = UpdateManager(
        current_version="0.3.6",
        cache_dir=tmp_path,
        manifest_url="https://example.test/signmaker-update.json",
        opener=opener,
    )

    with pytest.raises(UpdateManifestError, match="valid JSON"):
        manager.fetch_manifest()


def test_download_installer_verifies_sha256(tmp_path):
    installer = b"installer bytes"
    installer_hash = hashlib.sha256(installer).hexdigest()
    info = parse_update_manifest(
        _manifest(installer_hash=installer_hash),
        current_version="0.3.6",
    )

    def opener(_request, timeout):
        return FakeResponse(installer, headers={"Content-Length": str(len(installer))})

    manager = UpdateManager(
        current_version="0.3.6",
        cache_dir=tmp_path,
        manifest_url="https://example.test/signmaker-update.json",
        opener=opener,
    )
    progress = []

    installer_path = manager.download_installer(
        info,
        lambda downloaded, total: progress.append((downloaded, total)),
    )

    assert installer_path.exists()
    assert installer_path.read_bytes() == installer
    assert progress[-1] == (len(installer), len(installer))


def test_download_installer_removes_temp_file_on_sha256_mismatch(tmp_path):
    installer = b"installer bytes"
    info = parse_update_manifest(
        _manifest(installer_hash="0" * 64),
        current_version="0.3.6",
    )

    def opener(_request, timeout):
        return FakeResponse(installer)

    manager = UpdateManager(
        current_version="0.3.6",
        cache_dir=tmp_path,
        manifest_url="https://example.test/signmaker-update.json",
        opener=opener,
    )

    with pytest.raises(UpdateDownloadError, match="checksum mismatch"):
        manager.download_installer(info)

    assert not list(tmp_path.glob("*.download"))
    assert not list(tmp_path.glob("*.exe"))
