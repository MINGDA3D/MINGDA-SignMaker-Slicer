"""Localized user-facing messages for the online update workflow."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication

from src.business.update_manager import format_file_size


def format_update_file_size(size_bytes: int) -> str:
    """Format update asset sizes with a localized unknown value."""
    formatted = format_file_size(size_bytes)
    if formatted == "Unknown":
        return QCoreApplication.translate("UpdateMessages", "Unknown")
    return formatted


def translate_update_error(message: str) -> str:
    """Translate fixed update error text while preserving dynamic details."""
    text = str(message).strip()

    exact_messages = {
        "Update manifest must be a JSON object.": QCoreApplication.translate(
            "UpdateMessages",
            "Update manifest must be a JSON object."
        ),
        "Update manifest is missing version.": QCoreApplication.translate(
            "UpdateMessages",
            "Update manifest is missing version."
        ),
        "Update manifest is missing installer metadata.": QCoreApplication.translate(
            "UpdateMessages",
            "Update manifest is missing installer metadata."
        ),
        "Update installer is missing url.": QCoreApplication.translate(
            "UpdateMessages",
            "Update installer is missing url."
        ),
        "Update asset has an invalid SHA256 hash.": QCoreApplication.translate(
            "UpdateMessages",
            "Update asset has an invalid SHA256 hash."
        ),
        "Update asset has an invalid size_bytes value.": QCoreApplication.translate(
            "UpdateMessages",
            "Update asset has an invalid size_bytes value."
        ),
        "Update asset size_bytes cannot be negative.": QCoreApplication.translate(
            "UpdateMessages",
            "Update asset size_bytes cannot be negative."
        ),
        "Update manifest URL is not configured.": QCoreApplication.translate(
            "UpdateMessages",
            "Update manifest URL is not configured."
        ),
        "Update manifest is not valid JSON.": QCoreApplication.translate(
            "UpdateMessages",
            "Update manifest is not valid JSON."
        ),
    }
    if text in exact_messages:
        return exact_messages[text]

    app_prefix = "Update manifest is for "
    if text.startswith(app_prefix) and ", not " in text:
        detail = text[len(app_prefix):].rstrip(".")
        manifest_app, current_app = detail.split(", not ", 1)
        return "\n".join(
            (
                QCoreApplication.translate(
                    "UpdateMessages",
                    "The update manifest is for another application.",
                ),
                QCoreApplication.translate(
                    "UpdateMessages",
                    "Manifest app: {app}",
                ).format(app=manifest_app),
                QCoreApplication.translate(
                    "UpdateMessages",
                    "Current app: {app}",
                ).format(app=current_app),
            )
        )

    checksum_prefix = "Downloaded installer checksum mismatch. Expected "
    if text.startswith(checksum_prefix) and ", got " in text:
        detail = text[len(checksum_prefix):].rstrip(".")
        expected_hash, actual_hash = detail.split(", got ", 1)
        return "\n".join(
            (
                QCoreApplication.translate(
                    "UpdateMessages",
                    "Downloaded installer checksum mismatch.",
                ),
                QCoreApplication.translate(
                    "UpdateMessages",
                    "Expected SHA256: {hash}",
                ).format(hash=expected_hash),
                QCoreApplication.translate(
                    "UpdateMessages",
                    "Actual SHA256: {hash}",
                ).format(hash=actual_hash),
            )
        )

    prefix_messages = {
        "Unsupported version format: ": QCoreApplication.translate(
            "UpdateMessages",
            "Unsupported version format.",
        ),
        "Unsupported update manifest schema: ": QCoreApplication.translate(
            "UpdateMessages",
            "Unsupported update manifest schema."
        ),
        "Failed to fetch update manifest: ": QCoreApplication.translate(
            "UpdateMessages",
            "Failed to fetch update manifest."
        ),
        "Failed to download update installer: ": QCoreApplication.translate(
            "UpdateMessages",
            "Failed to download update installer."
        ),
        "Downloaded installer checksum mismatch. ": QCoreApplication.translate(
            "UpdateMessages",
            "Downloaded installer checksum mismatch."
        ),
    }

    for prefix, translated in prefix_messages.items():
        if text.startswith(prefix):
            detail = text[len(prefix):].strip()
            return f"{translated}\n{detail}" if detail else translated

    return text
