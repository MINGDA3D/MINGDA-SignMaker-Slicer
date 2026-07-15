"""Generate English subtitles and offline voiceovers for tutorial recordings."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import imageio_ffmpeg
except ImportError as exc:  # pragma: no cover - dependency check for local tool
    raise SystemExit("Missing dependency: run `python -m pip install imageio-ffmpeg`.") from exc


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "docs" / "MINGDA SignMaker V0.6.0 Video Tutorial"
OUTPUT_DIR = ROOT / "docs" / "MINGDA SignMaker V0.6.0 Video Tutorial Voiceover"


TUTORIAL_CUES: dict[str, list[str]] = {
    "1. MINGDA SignMaker Introduction.mp4": [
        "Welcome to MINGDA SignMaker. This course shows how to turn sign artwork into production-ready 3D printing files.",
        "SignMaker is built for illuminated letters, letter shells, acrylic faces, back plates, grooves, brims, and compensation.",
        "The normal workflow starts with a DXF, SVG, or saved SMP project file.",
        "After importing artwork, check the size, position, contours, and printer profile before changing process parameters.",
        "Process generates the slicing result, and 3D Preview lets you inspect height, edges, walls, slots, and bottom structures.",
        "The main production outputs are G-code, STL, Back Plate DXF, and Acrylic Face DXF.",
        "Unlike a general slicer, SignMaker focuses on sign-specific structures, mounting details, and panel fitting.",
        "In the next lessons, we will break this complete production loop into practical steps.",
    ],
    "2. MINGDA SignMaker Full Workflow Demo.mp4": [
        "This lesson gives a quick full workflow demonstration, without going deeply into every parameter.",
        "Start a new project, import the prepared DXF file, and immediately check the size and position on the bed.",
        "Choose the printer profile, then set only the basic shell height, layer height, wall, edge, and bottom options.",
        "Click Process, enter 3D Preview, and inspect the generated shell before exporting production files.",
        "At the end, export G-code, STL, Back Plate DXF, and Acrylic Face DXF for the correct production steps.",
    ],
    "3. MINGDA SignMaker Interface Overview.mp4": [
        "This lesson builds a map of the SignMaker interface so every area has a clear purpose.",
        "The Home page is used to create new projects, open existing work, and access recent projects.",
        "The Project page is where you edit shapes, manage objects, set parameters, and run Process.",
        "The Preview page shows the processed 3D result and helps you check layers before production.",
        "The top title bar gives access to Menu, Project, Preview, Process, Export, and other global actions.",
        "The Shape List on the left manages imported objects, while the central 2D canvas shows the bed and contours.",
        "The right parameter panel contains the main Shape, Machine, and Print settings used throughout this course.",
    ],
    "4.1 MINGDA SignMaker Change Language.mp4": [
        "This section shows how to change the software language from the menu.",
        "For overseas tutorial recording and overseas users, the English interface is recommended.",
        "After switching language, confirm that the main labels and panels update correctly.",
        "The setting is saved, so future sessions can continue with the selected language.",
    ],
    "4.2 MINGDA SignMaker Change Theme.mp4": [
        "This section shows the theme options: System, Dark, and Light.",
        "System follows the operating system theme, while Dark and Light apply a fixed appearance.",
        "Switch themes once during recording so users can clearly see the visual difference.",
    ],
    "4.3 MINGDA SignMaker Open Recent.mp4": [
        "Open Recent gives quick access to recently used DXF, SVG, and SMP files.",
        "Recent Projects on the Home page focuses on project files, especially saved SMP work.",
        "Use the correct recent-file entry depending on whether you need artwork or a full project.",
    ],
    "4.4 MINGDA SignMaker Show config-Tutorial-Check for updates-About-Exit.mp4": [
        "This menu group contains support and software information commands.",
        "Show Configuration Folder opens local settings, printer profiles, and files useful for troubleshooting.",
        "Tutorial and Check for Updates help users find learning material and keep the software current.",
        "About shows version information, and Exit closes the application after work is saved.",
    ],
    "5. MINGDA SignMaker Creating, Opening, Saving, and Reusing Projects.mp4": [
        "This lesson explains the difference between artwork files and project files.",
        "New Project clears the current workspace and starts a fresh task.",
        "Open File imports DXF or SVG artwork, while Open Project loads a saved SMP project.",
        "Save Project stores both geometry and parameters so the job can be edited later.",
        "Save As creates a reusable project copy for a customer order or a different production version.",
        "Do not treat exported G-code as a project file. Save the SMP file before closing or starting another job.",
    ],
    "6. MINGDA SignMaker Importing DXF SVG Files and Creating Text.mp4": [
        "This lesson covers the three common artwork sources: DXF, SVG, and text created inside SignMaker.",
        "DXF is usually exported from CAD, CorelDRAW, Illustrator, or other vector design tools.",
        "SVG is useful for logos, web vector artwork, and simple graphic shapes.",
        "After import, immediately check width, height, position, outer contours, inner holes, and broken lines.",
        "Text objects can be generated inside the software and then moved, scaled, processed, and exported like other shapes.",
    ],
    "7.1 MINGDA SignMaker 2D View Navigation.mp4": [
        "This section shows basic 2D view navigation.",
        "Use the mouse wheel to zoom in and out around the drawing area.",
        "Use right-button or middle-button drag to pan across the bed.",
        "Fit to Window and Reset View quickly bring the model back into a comfortable working view.",
    ],
    "7.2 MINGDA SignMaker Printable Area And No-Print Zone.mp4": [
        "The grid and bed outline help you judge real production size and position.",
        "The printable area comes from the selected machine profile.",
        "All shapes must stay inside the usable bed boundary before processing.",
        "Bed Exclude Area marks zones that should not receive printed paths.",
        "If the bed looks wrong, check the Machine settings before continuing.",
    ],
    "8. MIGNDA SignMaker Shape List and Object Management.mp4": [
        "The Shape List shows every shape object currently in the project.",
        "Clicking an item in the list selects the matching object on the 2D canvas.",
        "Multiple objects can be edited, moved, processed, and assigned parameters separately.",
        "For complex logos, first confirm object count and contour structure before slicing.",
        "Shape management is the foundation for print order, grouping, ungrouping, and later production checks.",
    ],
    "9. MINGDA SignMaker Basic Shape Editing Move Rotate Scale and Mirror.mp4": [
        "This lesson covers the most common shape editing tools.",
        "Move changes the object position on the bed, either by dragging or by entering precise X and Y values.",
        "Rotate changes the object direction, and the transform panel can apply exact angle values.",
        "Scale changes size. Keep Uniform Scale enabled when text or logos must not be distorted.",
        "Mirror Horizontal and Mirror Vertical flip the object across the chosen direction.",
        "After editing, check that the object still fits inside the printable area before processing.",
    ],
    "10. MINGDA SignMaker Advanced Shape Editing Boolean Group Ungroup Undo and Redo.mp4": [
        "This lesson introduces advanced editing used to clean up or combine imported shapes.",
        "Intersection keeps only the overlapping area between selected shapes.",
        "Difference subtracts one shape from another, which is useful for holes or cut-out effects.",
        "Group keeps multiple objects together for easier moving and processing.",
        "Ungroup or Explode Asset separates combined objects when they need individual editing.",
        "Use Undo and Redo after each operation to confirm that complex edits can be safely recovered.",
    ],
    "11. MINGDA SignMaker Start Points and Print Order.mp4": [
        "Start Point and Print Order affect the generated G-code path, not just the visual layout.",
        "Use Start Point to place the seam at a less visible or easier-to-finish location.",
        "Use Print Order when several letters or objects should be printed in a controlled sequence.",
        "Good order can reduce travel moves, stringing, and unnecessary movement across the job.",
        "After changing start points or print order, run Process again and check the result before export.",
    ],
    "12. MINGDA SignMaker Shell Height-Layer Height-Line Width-Wall Thickness.mp4": [
        "This lesson covers the most basic Shape parameters used in almost every job.",
        "Shell Height controls the total letter-shell height in the Z direction.",
        "Layer Height controls the vertical step between layers, affecting layer count, surface quality, and print time.",
        "Line Width is connected to nozzle size, extrusion width, and material flow.",
        "Wall Thickness controls strength, light transmission, and material usage.",
        "Z-direction values are aligned to the layer grid, so the final result uses complete printable layers.",
        "Whenever these core values change, run Process again before previewing or exporting.",
    ],
    "13. MINGDA SignMaker Creating Straight Beveled and Custom Wall Edges.mp4": [
        "Wall edge type is one of the core features of illuminated-letter production.",
        "Straight Wall creates a simple vertical shell for standard sign letters.",
        "Beveled Wall creates a sloped side surface for appearance, assembly space, or special structure needs.",
        "Bevel Direction controls whether the top is smaller or larger than the bottom.",
        "Bevel Horizontal Width controls the horizontal distance of the slope.",
        "Bottom Straight Height and Top Straight Height keep vertical sections near the base or face side.",
        "Custom Wall uses a preset or imported DXF profile when a customer needs a special edge shape.",
        "Compare Straight, Beveled, and Custom results in 3D Preview before choosing the final production style.",
    ],
    "14. MINGDA SignMaker Bottom Structures and Screw Holes.mp4": [
        "This lesson covers bottom structures used for back plates, screw holes, LED slots, and lower edge details.",
        "Start with None to understand the clean letter shell without any additional bottom structure.",
        "Bottom Shells creates a closed or reinforced bottom area, and Bottom Shell Thickness controls its depth.",
        "Screw holes are usually added only when the selected bottom structure can support them.",
        "Set Bottom Screw Hole Diameter according to the fastener and the actual assembly method.",
        "Back Plate Slot creates a straight mounting groove for a back plate.",
        "Back Plate V-Groove creates a V-shaped location feature for special installation methods.",
        "LED Strip Slot reserves space for light strips and can be applied around outer contours or inner holes.",
        "Bottom Edge Wrap and Bottom Outline are used for lower wrapping or outlining structures.",
        "Some bottom options are mutually exclusive, so enabling one structure may automatically disable another.",
        "After each bottom setting change, click Process and inspect the bottom region in 3D Preview.",
        "Use a letter with inner holes when checking whether bottom structures align correctly with inner walls.",
        "If screw holes do not appear, check that the bottom shell mode is enabled and the hole diameter is valid.",
        "If a groove looks wrong, review height, width, and mutual-exclusion settings before exporting.",
        "The goal is to verify assembly details in software before sending the job to production.",
    ],
    "15. MINGDA SignMaker Top Structures.mp4": [
        "This lesson explains top structures and how they relate to acrylic face installation.",
        "Use None when the shell does not need a top-side added structure.",
        "Top Shell creates a closed or reinforced top surface, controlled by Top Shell Thickness.",
        "Acrylic Face Slot creates a straight slot for positioning the face panel.",
        "Acrylic Face V-Groove creates a V-shaped locating structure for a different panel fitting method.",
        "Top Shell and face-slot structures should be treated as process choices, not stacked casually.",
        "After changing top settings, Process again and check the upper structure in 3D Preview.",
    ],
    "16.1 MINGDA SignMaker Anti-Warp Brim.mp4": [
        "Anti-Warp Brim helps reduce edge lifting on large or difficult letter shapes.",
        "Brim Height controls how high the brim structure is printed.",
        "Brim Speed controls how fast the brim paths are produced.",
        "Breakaway Gap controls how easily the brim separates from the finished part.",
        "Outer Brim supports outside edges, while Inner Brim can support holes or internal openings.",
        "Use 3D Preview to confirm the brim is present where needed and not interfering with assembly features.",
    ],
    "16.2 MINGDA SignMaker Letter Bridges.mp4": [
        "Letter Bridges connect separated letters or strokes so they can be produced as a stable connected set.",
        "Use this feature when separate objects need to stay aligned during printing or installation.",
        "Bridge Type provides shapes such as Triangle and Diamond for different visual and structural needs.",
        "Auto-Detect Bridge Points can suggest usable connection locations.",
        "Bridge Width controls the physical width of each bridge.",
        "Bridge Bevel Height and Bridge Base Height control how the bridge transitions into the letter body.",
        "Check bridges in both 2D and 3D so they are strong enough but not visually intrusive.",
        "After adding or changing bridges, run Process again before exporting G-code or STL.",
    ],
    "16.3 MINGDA SignMaker DXF Export Compensation.mp4": [
        "DXF Export Compensation adjusts back plate and acrylic face outlines for real manufacturing fit.",
        "Outer contour clearance changes the outside size of the exported panel or plate.",
        "Inner hole clearance changes the size of internal openings.",
        "Laser kerf compensation accounts for material removed by the cutting process.",
        "Changing compensation values affects exported DXF files, not just the screen display.",
        "Export test files and compare outlines when tuning fit for a specific material or laser process.",
    ],
    "17. MINGDA SignMaker Machine Setup and Hardware Settings.mp4": [
        "The Machine tab controls printer profiles and hardware-related parameters.",
        "Choose the correct MINGDA printer profile and nozzle size before processing a job.",
        "Printable Area X, Y, and Z define the usable build volume shown on the canvas.",
        "Bed Exclude Area marks zones where the print head or model should not go.",
        "Nozzle diameter, filament diameter, retract settings, and Z-hop settings affect generated motion and extrusion behavior.",
    ],
    "19.1 MINGDA SignMaker Speed Tempetature Cooling Settings.mp4": [
        "The Print tab controls motion, temperature, and cooling parameters.",
        "Outer wall, inner wall, and general path speed affect surface quality and print time.",
        "Small details, slots, and steps usually should not be printed too fast.",
        "Temperature should be tuned for the material brand, nozzle size, and printer condition.",
        "Cooling settings affect small features and layer bonding, so use defaults as a starting point and adjust with test prints.",
    ],
    "19.2 MINGDA SignMaker Color Change-Prime Tower-Start and End Gcode.mp4": [
        "This lesson covers color change, Prime Tower, and start or end G-code settings.",
        "Enable Color Change when the job needs a material or color switch at a specific height.",
        "Change At Height defines where the color change happens in the Z direction.",
        "Macro Index selects the machine-specific command used for the change process.",
        "Prime Tower helps purge and stabilize material after a color or material change.",
        "Tower position, size, and infill density control where the purge tower prints and how much material it uses.",
        "Start and End G-code are powerful machine scripts, so beginners should edit them only when they understand the printer requirements.",
    ],
    "20. MINGAD SignMaker Process.mp4": [
        "Process generates the actual slicing result from the current shapes and parameters.",
        "Whenever geometry, process settings, start points, or print order change, run Process again.",
        "G-code and STL export usually depend on having a current processed result.",
        "Before processing, check that the model is inside the printable area and the correct printer profile is selected.",
        "After processing, go to Preview and inspect the result instead of exporting blindly.",
    ],
    "21. MINGDA SignMaker 3D Preview.mp4": [
        "3D Preview is the final inspection step before export.",
        "Use it to check shell height, edge type, grooves, bottom shells, brims, and internal openings.",
        "Rotate the view and inspect both outside walls and inner holes.",
        "If the structure is wrong, return to Project, adjust parameters, Process again, and then preview once more.",
    ],
    "22. MINGDA SignMaker Export G-code-STL-Back Plate DXF-Acrylic Face DXF.mp4": [
        "This lesson explains the main export formats and when to use each one.",
        "Export G-code for the printer when the job is ready for production.",
        "Export STL when you need a 3D model for checking, archiving, or secondary slicing.",
        "Export Back Plate DXF for laser cutting or machining the back plate outline.",
        "Export Acrylic Face DXF for cutting the acrylic face panel.",
        "Remember that G-code and STL need a valid Process result, while DXF export needs valid contours and compensation settings.",
    ],
    "23.1 MINGDA SignMaker Decorative Face Panel Patterns.mp4": [
        "Decorative face panel patterns are created through a two-step workflow.",
        "First, use SignMaker to create a closed bottom shell and confirm the surface in 3D Preview.",
        "Then export STL and open it in MINGDA OrcaSlicer for secondary slicing.",
        "In OrcaSlicer, adjust top and bottom shells, infill pattern, density, angle, and related settings.",
        "The visible decorative texture comes from OrcaSlicer infill behavior, not from a final pattern generator inside SignMaker.",
        "Always inspect the sliced paths before sending the decorative panel workflow to production.",
    ],
    "23.2 MINGDA SignMaker Grid Fill and Solid Letters.mp4": [
        "Solid letters and grid-fill effects also use SignMaker together with MINGDA OrcaSlicer.",
        "For solid letters, close unnecessary face slots and enable Top Shell in SignMaker.",
        "Set Top Shell Thickness, run Process, and check the closed top surface in Preview.",
        "Export STL and import it into OrcaSlicer for the final slicing workflow.",
        "Enable printable overhang behavior when needed, then tune infill pattern, density, and direction.",
        "For grid-fill style results, the final path appearance is controlled by OrcaSlicer infill settings.",
        "Check top surfaces, internal fill, overhang regions, holes, and outer contours before production.",
    ],
    "24. MINGDA SignMaker Common FAQ and Pitfalls.mp4": [
        "This FAQ lesson focuses on common mistakes and how to avoid them.",
        "If imported size is wrong, check the source-file units and the measured width and height after import.",
        "If artwork is outside the bed, confirm the printer profile and printable area settings.",
        "If G-code or STL cannot export, check whether parameters changed after the last Process operation.",
        "If bottom structures are missing, review the selected Bottom mode and mutual-exclusion options.",
        "If screw holes do not work, confirm that a compatible bottom shell structure is enabled.",
        "If color change does not happen, check Change At Height, Macro Index, and export G-code rather than STL.",
        "If panel or back plate DXF size is wrong, adjust DXF Export Compensation.",
        "If seams or travel order are not ideal, set Start Point and Print Order, then Process again.",
        "Wall, Top, and Bottom sub-options can be mutually exclusive within the same structural category.",
        "For every issue, reproduce the symptom, identify the related setting, correct it, and preview again.",
        "A careful check before export prevents most production failures and reduces support time.",
    ],
}


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def run(command: list[str], *, quiet: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail}")
    if not quiet and result.stdout.strip():
        print(result.stdout.strip())
    return result


def probe_duration(ffmpeg: str, path: Path) -> float:
    result = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr + result.stdout)
    if not match:
        raise RuntimeError(f"Could not read duration: {path}")
    return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))


def format_srt_time(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def timed_cues(lines: list[str], duration: float) -> list[Cue]:
    start_margin = 0.5
    end_margin = 0.45
    available = max(1.0, duration - start_margin - end_margin)
    weights = [max(2.2, len(line.split()) / 2.25 + 0.8) for line in lines]
    total_weight = sum(weights)
    cues: list[Cue] = []
    cursor = start_margin
    for index, (line, weight) in enumerate(zip(lines, weights), start=1):
        span = available * weight / total_weight
        start = cursor
        end = min(duration - end_margin, cursor + span - 0.08)
        if index == len(lines):
            end = duration - end_margin
        cues.append(Cue(index=index, start=start, end=max(start + 0.8, end), text=line))
        cursor += span
    return cues


def write_srt(path: Path, cues: list[Cue]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for cue in cues:
            handle.write(f"{cue.index}\n")
            handle.write(f"{format_srt_time(cue.start)} --> {format_srt_time(cue.end)}\n")
            handle.write(f"{cue.text}\n\n")


def write_script(path: Path, video_name: str, cues: list[Cue]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{video_name}\n")
        handle.write("=" * len(video_name) + "\n\n")
        for cue in cues:
            handle.write(f"[{format_srt_time(cue.start)} --> {format_srt_time(cue.end)}] {cue.text}\n")


def build_atempo(value: float) -> str:
    if value <= 1.01:
        return "anull"
    parts: list[float] = []
    remaining = value
    while remaining > 2.0:
        parts.append(2.0)
        remaining /= 2.0
    parts.append(remaining)
    return ",".join(f"atempo={part:.5f}" for part in parts)


def ensure_tts_wavs(cues_by_video: dict[str, list[Cue]], cue_dir: Path, voice: str, rate: int, overwrite: bool) -> None:
    jobs = []
    for video_name, cues in cues_by_video.items():
        stem = Path(video_name).stem
        for cue in cues:
            wav_path = cue_dir / stem / f"{cue.index:03}.wav"
            if overwrite or not wav_path.exists():
                jobs.append({"out": str(wav_path), "text": cue.text})
    if not jobs:
        return

    job_file = cue_dir / "tts_jobs.json"
    ps_file = cue_dir / "generate_tts.ps1"
    cue_dir.mkdir(parents=True, exist_ok=True)
    job_file.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    ps_file.write_text(
        "\n".join(
            [
                "param([string]$JobFile, [string]$Voice, [int]$Rate)",
                "Add-Type -AssemblyName System.Speech",
                "$jobs = Get-Content -LiteralPath $JobFile -Raw -Encoding UTF8 | ConvertFrom-Json",
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
                "if ($Voice) { $s.SelectVoice($Voice) }",
                "$s.Rate = $Rate",
                "$s.Volume = 100",
                "foreach ($job in $jobs) {",
                "  $dir = Split-Path -Parent $job.out",
                "  if (!(Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }",
                "  $s.SetOutputToWaveFile($job.out)",
                "  $s.Speak([string]$job.text) | Out-Null",
                "  $s.SetOutputToNull()",
                "}",
                "$s.Dispose()",
            ]
        ),
        encoding="utf-8",
    )
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_file), str(job_file), voice, str(rate)], quiet=True)


def fit_cue_audio(ffmpeg: str, wav_path: Path, fit_path: Path, target_duration: float, overwrite: bool) -> Path:
    if fit_path.exists() and not overwrite:
        return fit_path
    source_duration = probe_duration(ffmpeg, wav_path)
    ratio = source_duration / max(0.5, target_duration)
    filter_audio = build_atempo(ratio)
    run([ffmpeg, "-y", "-i", str(wav_path), "-filter:a", filter_audio, "-ac", "1", "-ar", "44100", str(fit_path)], quiet=True)
    return fit_path


def mix_video_audio(ffmpeg: str, video_name: str, cues: list[Cue], cue_dir: Path, audio_path: Path, duration: float, overwrite: bool) -> None:
    if audio_path.exists() and not overwrite:
        return
    stem = Path(video_name).stem
    inputs: list[str] = []
    labels: list[str] = []
    filters: list[str] = []
    for idx, cue in enumerate(cues):
        wav_path = cue_dir / stem / f"{cue.index:03}.wav"
        fit_path = cue_dir / stem / f"{cue.index:03}.fit.wav"
        fitted = fit_cue_audio(ffmpeg, wav_path, fit_path, cue.end - cue.start - 0.1, overwrite)
        inputs.extend(["-i", str(fitted)])
        delay_ms = int(round(cue.start * 1000))
        filters.append(f"[{idx}:a]adelay={delay_ms}[a{idx}]")
        labels.append(f"[a{idx}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,apad,loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    run([ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-t", f"{duration:.3f}", "-c:a", "aac", "-b:a", "160k", str(audio_path)], quiet=True)


def mux_video(ffmpeg: str, source: Path, audio: Path, srt: Path, output: Path, overwrite: bool) -> None:
    if output.exists() and not overwrite:
        return
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(source),
            "-i",
            str(audio),
            "-i",
            str(srt),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-map",
            "2:0",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-c:s",
            "mov_text",
            "-metadata:s:a:0",
            "language=eng",
            "-metadata:s:s:0",
            "language=eng",
            "-metadata:s:s:0",
            "title=English subtitles",
            str(output),
        ],
        quiet=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--voice", default="Microsoft Zira Desktop")
    parser.add_argument("--rate", type=int, default=0)
    parser.add_argument("--only", action="append", help="Process only files containing this text. Can be repeated.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    input_videos = sorted(args.input_dir.glob("*.mp4"), key=natural_key)
    if args.only:
        needles = [item.lower() for item in args.only]
        input_videos = [path for path in input_videos if any(needle in path.name.lower() for needle in needles)]
    missing = [path.name for path in input_videos if path.name not in TUTORIAL_CUES]
    if missing:
        raise SystemExit("No cue script for:\n" + "\n".join(missing))

    srt_dir = args.output_dir / "subtitles"
    script_dir = args.output_dir / "scripts"
    audio_dir = args.output_dir / "audio"
    video_dir = args.output_dir / "videos"
    cue_dir = args.output_dir / "_cue_wavs"
    for directory in (srt_dir, script_dir, audio_dir, video_dir, cue_dir):
        directory.mkdir(parents=True, exist_ok=True)

    durations = {path.name: probe_duration(ffmpeg, path) for path in input_videos}
    cues_by_video = {name: timed_cues(TUTORIAL_CUES[name], durations[name]) for name in durations}
    for path in input_videos:
        stem = path.stem
        cues = cues_by_video[path.name]
        write_srt(srt_dir / f"{stem}.srt", cues)
        write_script(script_dir / f"{stem}.txt", path.name, cues)

    ensure_tts_wavs(cues_by_video, cue_dir, args.voice, args.rate, args.overwrite)

    for index, source in enumerate(input_videos, start=1):
        stem = source.stem
        print(f"[{index}/{len(input_videos)}] {source.name}")
        duration = durations[source.name]
        srt_path = srt_dir / f"{stem}.srt"
        audio_path = audio_dir / f"{stem}.m4a"
        output_path = video_dir / f"{stem} - English Voiceover.mp4"
        mix_video_audio(ffmpeg, source.name, cues_by_video[source.name], cue_dir, audio_path, duration, args.overwrite)
        mux_video(ffmpeg, source, audio_path, srt_path, output_path, args.overwrite)

    print(f"Done. Output: {args.output_dir}")


if __name__ == "__main__":
    main()
