# Packaging And Online Update Release Workflow

This document records the Windows packaging and GitHub Release workflow for
MINGDA SignMaker. The current release format uses one public installer only:

```text
MINGDA-SignMaker-Setup-<version>.exe
signmaker-update.json
```

The updater checks this manifest by default:

```text
https://github.com/mingda3d/MINGDA-SignMaker-Slicer/releases/latest/download/signmaker-update.json
```

If the public release repository changes, update the default manifest URL in
`src/app_info.py`. For local testing, set `MINGDA_SIGNMAKER_UPDATE_URL` before
starting the app.

## Release Checklist

Before building:

1. Pick the release version, for example `0.3.7`.
2. Update `VERSION` to the same version.
3. Update `CHANGELOG.md` with the release notes.
4. Confirm the app version shown in the About dialog uses `get_app_version()`.
5. Run the relevant tests before packaging.
6. Do not commit generated files from `build/` or `dist/`.

The version passed to Inno Setup only changes the installer metadata and output
file name. It does not change the version embedded in the PyInstaller exe. If
the installer name says `0.3.7` but the app still shows `0.3.6`, update
`VERSION` and rebuild the PyInstaller exe.

## Prerequisites

Install dependencies in the virtual environment:

```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Required packaging tools:

```text
PyInstaller: installed through requirements / virtual environment
Inno Setup 6: C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

The current release installer is built from:

```text
installer\mingda_signmaker_setup.iss
```

The older NSIS script is not the release packaging path.

## Build The Protected Exe

Only the dongle-protected application is released. The build switch is the
existing `CODE_DOG=1` environment variable.

```powershell
$version = "0.3.7"

try {
  $env:CODE_DOG = "1"
  .\.venv\Scripts\python -m PyInstaller --clean --noconfirm "SignMaker Slicer.spec"
}
finally {
  Remove-Item Env:\CODE_DOG -ErrorAction SilentlyContinue
}
```

Expected output:

```text
dist\MINGDA SignMaker.exe
```

## Build The Installer

Compile the modern Inno Setup installer:

```powershell
$version = "0.3.7"
$versionInfo = "$($version).0"

& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
  "/DMyAppVersion=$version" `
  "/DMyAppVersionInfo=$versionInfo" `
  "installer\mingda_signmaker_setup.iss"
```

Expected output:

```text
dist\MINGDA-SignMaker-Setup-0.3.7.exe
```

The Inno script uses:

```text
WizardStyle=modern
OutputDir=..\dist
OutputBaseFilename=MINGDA-SignMaker-Setup-{#MyAppVersion}
SetupIconFile=..\resources\logos\MINGDA_logo.ico
```

It installs the single PyInstaller exe, creates optional desktop shortcuts, and
offers optional file associations for `.smp`, `.dxf`, and `.svg`.

## Generate The Update Manifest

Create a release notes text file first, for example:

```text
release-notes.txt
```

Release notes writing rules:

1. Use English only.
2. Use this exact first-line title format: `MINGDA SignMaker V<version> Official Release`.
3. Keep the notes concise for the update dialog.
4. Include only user-visible changes, such as new features, visible workflow improvements, compatibility improvements, or bug fixes users can notice.
5. Do not mention internal tests, source file changes, implementation details, packaging metadata, version synchronization, hashes, CI, or other maintenance-only work.
6. Prefer 1 to 3 short bullet points using plain `- ` bullets.

Example:

```text
MINGDA SignMaker V0.3.8 Official Release

- Improved the bottom arc transition for U-shaped edges for smoother slicing.
- Improved G-code export compatibility with preview and parsing software.
```

After the installer exists, generate `signmaker-update.json`:

```powershell
$version = "0.3.7"

.\.venv\Scripts\python tools\generate_update_manifest.py `
  --version $version `
  --release-url "https://github.com/mingda3d/MINGDA-SignMaker-Slicer/releases/tag/v$version" `
  --installer "dist\MINGDA-SignMaker-Setup-$version.exe" `
  --installer-url "https://github.com/mingda3d/MINGDA-SignMaker-Slicer/releases/download/v$version/MINGDA-SignMaker-Setup-$version.exe" `
  --notes-file "release-notes.txt" `
  --output "dist\signmaker-update.json"
```

The generated manifest contains the installer URL, SHA256 hash, and file size:

```json
{
  "schema": 1,
  "app": "MINGDA SignMaker",
  "version": "0.3.7",
  "release_url": "https://github.com/mingda3d/MINGDA-SignMaker-Slicer/releases/tag/v0.3.7",
  "notes": "Release notes text",
  "installer": {
    "url": "https://github.com/mingda3d/MINGDA-SignMaker-Slicer/releases/download/v0.3.7/MINGDA-SignMaker-Setup-0.3.7.exe",
    "sha256": "...",
    "size_bytes": 123456789
  }
}
```

There are no `normal`, `code_dog`, or `variants` fields in the release manifest.

## Publish To GitHub Releases

Create or use the public GitHub repository that will host release assets. The
repository should contain the source code and packaging scripts, including:

```text
VERSION
CHANGELOG.md
SignMaker Slicer.spec
installer\mingda_signmaker_setup.iss
tools\generate_update_manifest.py
src\
resources\
requirements.txt
```

Do not commit generated installers or PyInstaller output. Upload them as Release
assets instead.

Release steps:

1. Create a tag named `v<version>`, for example `v0.3.7`.
2. Create a GitHub Release for that tag.
3. Upload `dist\MINGDA-SignMaker-Setup-<version>.exe`.
4. Upload `dist\signmaker-update.json`.
5. Publish the release.
6. Verify this URL opens the manifest:

```text
https://github.com/mingda3d/MINGDA-SignMaker-Slicer/releases/latest/download/signmaker-update.json
```

## Verification

Before publishing:

```powershell
$version = "0.3.7"
Get-Item "dist\MINGDA-SignMaker-Setup-$version.exe"
Get-Item "dist\signmaker-update.json"
```

Check that:

1. The app starts from `dist\MINGDA SignMaker.exe`.
2. The About dialog shows the same version as `VERSION`.
3. The installer installs and launches the app.
4. The installer upgrades an existing installation without requiring manual
   uninstall.
5. The manifest `installer.url` points to the final GitHub Release asset.
6. The manifest `sha256` matches the uploaded installer.
7. The app's `Check for Updates` action can see the new release.

## Troubleshooting

If `ISCC.exe` is not found, install Inno Setup 6 or replace the command path with
the actual install location.

If the installer builds but the app shows an old version, update `VERSION`, run
PyInstaller again, and then run Inno Setup again.

If PyInstaller prints warnings about optional DLLs or hidden imports, inspect
the final executable first. Warnings are not always fatal, but a missing runtime
dependency must be fixed before publishing.

If the updater downloads but refuses to run the installer, regenerate the
manifest after rebuilding the installer. The SHA256 in `signmaker-update.json`
must match the exact uploaded `.exe`.
