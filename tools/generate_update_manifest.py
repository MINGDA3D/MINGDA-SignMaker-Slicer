#!/usr/bin/env python3
"""Generate the GitHub Release update manifest for MINGDA SignMaker."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _asset(file_path: Path, url: str) -> dict:
    return {
        "url": url,
        "sha256": _sha256(file_path),
        "size_bytes": file_path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate signmaker-update.json for a GitHub Release.",
    )
    parser.add_argument("--version", required=True, help="Release version, for example 0.3.7")
    parser.add_argument("--release-url", required=True, help="GitHub Release page URL")
    parser.add_argument("--installer", required=True, type=Path)
    parser.add_argument("--installer-url", required=True)
    parser.add_argument("--notes", default="", help="Plain-text release notes")
    parser.add_argument("--notes-file", type=Path, help="Read release notes from a file")
    parser.add_argument(
        "--output",
        default=Path("dist/signmaker-update.json"),
        type=Path,
        help="Output JSON manifest path",
    )
    args = parser.parse_args()

    notes = args.notes
    if args.notes_file:
        notes = args.notes_file.read_text(encoding="utf-8").strip()

    manifest = {
        "schema": 1,
        "app": "MINGDA SignMaker",
        "version": args.version.lstrip("v"),
        "release_url": args.release_url,
        "notes": notes,
        "installer": _asset(args.installer, args.installer_url),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
