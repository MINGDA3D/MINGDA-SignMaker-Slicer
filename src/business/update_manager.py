"""Online update checks and installer download helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.app_info import APP_NAME, get_update_manifest_url


SCHEMA_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 20
DOWNLOAD_TIMEOUT_SECONDS = 120
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class UpdateError(RuntimeError):
    """Base class for online update failures."""


class UpdateNetworkError(UpdateError):
    """Raised when the update manifest or installer cannot be fetched."""


class UpdateManifestError(UpdateError):
    """Raised when an update manifest is malformed or unsupported."""


class UpdateDownloadError(UpdateError):
    """Raised when an installer download or checksum validation fails."""


@dataclass(frozen=True)
class UpdateAsset:
    """Installer asset metadata for an update."""

    url: str
    sha256: str
    size_bytes: int = 0


@dataclass(frozen=True)
class UpdateInfo:
    """A newer update selected for this application."""

    current_version: str
    version: str
    release_url: str
    notes: str
    asset: UpdateAsset


ProgressCallback = Callable[[int, int], None]


def parse_semver(version: str) -> tuple[int, int, int]:
    """Parse a strict numeric x.y.z version, allowing a leading v."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(version).strip())
    if not match:
        raise ValueError(f"Unsupported version format: {version!r}")
    return tuple(int(part) for part in match.groups())


def normalize_version(version: str) -> str:
    """Return a normalized x.y.z version string."""
    return ".".join(str(part) for part in parse_semver(version))


def is_newer_version(latest_version: str, current_version: str) -> bool:
    """Return whether latest_version is newer than current_version."""
    return parse_semver(latest_version) > parse_semver(current_version)


def format_file_size(size_bytes: int) -> str:
    """Format a byte count for update dialogs."""
    if size_bytes <= 0:
        return "Unknown"

    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def parse_update_manifest(
    manifest: dict[str, Any],
    *,
    current_version: str,
) -> UpdateInfo:
    """Parse and validate the update manifest."""
    if not isinstance(manifest, dict):
        raise UpdateManifestError("Update manifest must be a JSON object.")

    schema = manifest.get("schema")
    if schema != SCHEMA_VERSION:
        raise UpdateManifestError(f"Unsupported update manifest schema: {schema!r}")

    app_name = str(manifest.get("app", "")).strip()
    if app_name and app_name != APP_NAME:
        raise UpdateManifestError(f"Update manifest is for {app_name}, not {APP_NAME}.")

    try:
        version = normalize_version(str(manifest["version"]))
    except KeyError as exc:
        raise UpdateManifestError("Update manifest is missing version.") from exc
    except ValueError as exc:
        raise UpdateManifestError(str(exc)) from exc

    asset_data = manifest.get("installer")
    if not isinstance(asset_data, dict):
        raise UpdateManifestError("Update manifest is missing installer metadata.")

    installer_url = str(asset_data.get("url", "")).strip()
    sha256 = str(asset_data.get("sha256", "")).strip().lower()
    if not installer_url:
        raise UpdateManifestError("Update installer is missing url.")
    if not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise UpdateManifestError("Update asset has an invalid SHA256 hash.")

    size_bytes = asset_data.get("size_bytes", 0)
    try:
        size_bytes = int(size_bytes or 0)
    except (TypeError, ValueError) as exc:
        raise UpdateManifestError("Update asset has an invalid size_bytes value.") from exc
    if size_bytes < 0:
        raise UpdateManifestError("Update asset size_bytes cannot be negative.")

    release_url = str(manifest.get("release_url", "")).strip()
    notes = str(manifest.get("notes", "")).strip()
    return UpdateInfo(
        current_version=normalize_version(current_version),
        version=version,
        release_url=release_url,
        notes=notes,
        asset=UpdateAsset(
            url=installer_url,
            sha256=sha256,
            size_bytes=size_bytes,
        ),
    )


class UpdateManager:
    """Fetch update manifests and download verified installers."""

    def __init__(
        self,
        *,
        current_version: str,
        cache_dir: Path,
        manifest_url: Optional[str] = None,
        opener: Optional[Callable[..., Any]] = None,
    ):
        self.current_version = normalize_version(current_version)
        self.cache_dir = Path(cache_dir)
        self.manifest_url = manifest_url or get_update_manifest_url()
        self._opener = opener or urlopen

    def check_for_update(self) -> Optional[UpdateInfo]:
        """Return update info when a newer version exists, otherwise None."""
        manifest = self.fetch_manifest()
        update_info = parse_update_manifest(
            manifest,
            current_version=self.current_version,
        )
        if not is_newer_version(update_info.version, self.current_version):
            return None
        return update_info

    def fetch_manifest(self) -> dict[str, Any]:
        """Fetch and decode the configured JSON update manifest."""
        if not self.manifest_url:
            raise UpdateManifestError("Update manifest URL is not configured.")

        try:
            with self._open_url(self.manifest_url, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
                raw_data = response.read()
        except (HTTPError, URLError, OSError) as exc:
            raise UpdateNetworkError(f"Failed to fetch update manifest: {exc}") from exc

        try:
            data = json.loads(raw_data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateManifestError("Update manifest is not valid JSON.") from exc

        if not isinstance(data, dict):
            raise UpdateManifestError("Update manifest must be a JSON object.")
        return data

    def download_installer(
        self,
        update_info: UpdateInfo,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> Path:
        """Download and SHA256-verify the selected installer."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        target_path = self.cache_dir / self._installer_file_name(update_info)

        if target_path.exists() and file_sha256(target_path) == update_info.asset.sha256:
            if progress_callback:
                size = target_path.stat().st_size
                progress_callback(size, size)
            return target_path

        temp_path = target_path.with_name(target_path.name + ".download")
        temp_path.unlink(missing_ok=True)

        hasher = hashlib.sha256()
        downloaded = 0
        total = update_info.asset.size_bytes

        try:
            with self._open_url(
                update_info.asset.url,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            ) as response:
                header_total = _content_length(response)
                if header_total > 0:
                    total = header_total

                with open(temp_path, "wb") as output:
                    while True:
                        chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                        if not chunk:
                            break
                        output.write(chunk)
                        hasher.update(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total)
        except (HTTPError, URLError, OSError) as exc:
            temp_path.unlink(missing_ok=True)
            raise UpdateDownloadError(f"Failed to download update installer: {exc}") from exc

        digest = hasher.hexdigest().lower()
        if digest != update_info.asset.sha256:
            temp_path.unlink(missing_ok=True)
            raise UpdateDownloadError(
                "Downloaded installer checksum mismatch. "
                f"Expected {update_info.asset.sha256}, got {digest}."
            )

        temp_path.replace(target_path)
        if progress_callback:
            size = target_path.stat().st_size
            progress_callback(size, size)
        return target_path

    def _open_url(self, url: str, *, timeout: int):
        request = Request(
            url,
            headers={
                "User-Agent": f"{APP_NAME}/{self.current_version}",
                "Accept": "application/json, application/octet-stream;q=0.9, */*;q=0.8",
            },
        )
        return self._opener(request, timeout=timeout)

    def _installer_file_name(self, update_info: UpdateInfo) -> str:
        parsed_name = Path(urlparse(update_info.asset.url).path).name
        if not parsed_name.lower().endswith(".exe"):
            parsed_name = f"MINGDA-SignMaker-Setup-{update_info.version}.exe"
        return _safe_file_name(parsed_name)


def file_sha256(file_path: Path) -> str:
    """Return the SHA256 hex digest for a local file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as input_file:
        for chunk in iter(lambda: input_file.read(DOWNLOAD_CHUNK_SIZE), b""):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def _content_length(response: Any) -> int:
    headers = getattr(response, "headers", None)
    if not headers:
        return 0
    try:
        return int(headers.get("Content-Length", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _safe_file_name(file_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]", "_", file_name).strip(" .") or "update.exe"
