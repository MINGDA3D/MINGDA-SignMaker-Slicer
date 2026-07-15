"""Burn content-based English subtitles into SignMaker tutorial recordings."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import imageio_ffmpeg
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: run `python -m pip install imageio-ffmpeg`.") from exc


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "docs" / "MINGDA SignMaker V0.6.0 Video Tutorial"
OUTPUT_DIR = ROOT / "docs" / "MINGDA SignMaker V0.6.0 Content Subtitles"


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


SUBTITLES: dict[str, list[Cue]] = {
    "1. MINGDA SignMaker Introduction.mp4": [
        Cue(0.5, 6.0, "MINGDA SignMaker is a dedicated slicer for illuminated sign letter production."),
        Cue(6.0, 13.0, "It supports letter shells, acrylic face panels, and back plates."),
        Cue(13.0, 17.5, "The goal is to turn 2D sign artwork into printable production files."),
        Cue(17.5, 24.5, "The standard workflow starts with preparing the shape file."),
        Cue(24.5, 31.0, "Create a project, import artwork, set process parameters, and run Process."),
        Cue(31.0, 35.3, "Check the result in 3D Preview before exporting production files."),
        Cue(35.3, 43.5, "The main input files are DXF, SVG, and SMP project files."),
        Cue(43.5, 50.0, "DXF and SVG provide artwork; SMP saves geometry, settings, and job data."),
        Cue(50.0, 58.5, "The main outputs are G-code, STL, Back Plate DXF, and Acrylic Face DXF."),
        Cue(58.5, 67.5, "G-code is sent to the printer; STL is used for checking or secondary workflows."),
        Cue(67.5, 72.0, "The two DXF outputs are used for the back plate and acrylic face."),
        Cue(72.0, 81.0, "A generic slicer mainly works with existing 3D models and common print settings."),
        Cue(81.0, 91.5, "SignMaker starts from 2D sign shapes and generates shell height, wall profiles, grooves, slots, and compensation."),
        Cue(91.5, 98.6, "Use SignMaker when sign production needs fitting details that a normal slicer does not provide."),
    ],
    "2. MINGDA SignMaker Full Workflow Demo.mp4": [
        Cue(0.5, 3.5, "Start from Home and open the prepared tutorial file."),
        Cue(3.5, 5.8, "Select the DXF example from the tutorial folder."),
        Cue(5.8, 12.8, "After import, the MD outline appears on the Project canvas inside the bed."),
        Cue(12.8, 16.5, "Review the basic shape settings before generating the result."),
        Cue(16.5, 21.0, "Open Preview to inspect the generated 3D shell."),
        Cue(21.0, 27.5, "Open the result in the slicer environment for a production check."),
        Cue(27.5, 33.8, "Slice preview shows the generated toolpaths before saving."),
        Cue(33.8, 39.2, "Export the production file only after the preview confirms the result."),
    ],
    "3. MINGDA SignMaker Interface Overview.mp4": [
        Cue(0.5, 7.0, "Home is the starting page for new projects, open files, and recent work."),
        Cue(7.0, 19.0, "The Menu contains global actions such as files, language, theme, tutorials, updates, and About."),
        Cue(19.0, 31.5, "New Project and Open File are the main entry points from Home."),
        Cue(31.5, 42.5, "The Project page combines Shape List, toolbar, 2D canvas, and the parameter panel."),
        Cue(42.5, 57.0, "The Shape tab contains Wall, Bottom, Top, and Other process settings."),
        Cue(57.0, 70.0, "Machine and Print tabs control printer profile, hardware, speed, temperature, and cooling."),
        Cue(70.0, 85.7, "Preview switches from the 2D canvas to the processed 3D result for inspection."),
    ],
    "4.1 MINGDA SignMaker Change Language.mp4": [
        Cue(0.5, 4.0, "Open Menu from the Home page."),
        Cue(4.0, 15.0, "Use the Language submenu to choose another interface language."),
        Cue(15.0, 21.5, "After selecting a language, SignMaker asks for confirmation or restart."),
        Cue(21.5, 31.5, "The application restarts so the interface can reload with the new language."),
        Cue(31.5, 36.7, "The Home page now appears in the selected language."),
    ],
    "4.2 MINGDA SignMaker Change Theme.mp4": [
        Cue(0.5, 4.0, "Open Menu and go to the Theme options."),
        Cue(4.0, 8.5, "Switch to Light theme to check the bright interface style."),
        Cue(8.5, 14.5, "The same menu can also return the software to Dark or System theme."),
        Cue(14.5, 20.0, "Choose the theme that matches the recording or production environment."),
    ],
    "4.3 MINGDA SignMaker Open Recent.mp4": [
        Cue(0.5, 4.5, "Open Recent lists recently used artwork and project files."),
        Cue(4.5, 9.5, "If the current work is unsaved, confirm before opening another file."),
        Cue(9.5, 15.5, "Use the file dialog when a recent entry needs to be reselected."),
        Cue(15.5, 21.5, "The selected recent file opens on the Project canvas."),
        Cue(21.5, 28.0, "Check the loaded shape before continuing with parameters or export."),
    ],
    "4.4 MINGDA SignMaker Show config-Tutorial-Check for updates-About-Exit.mp4": [
        Cue(0.5, 6.0, "Show Configuration Folder opens local settings, profiles, and support files."),
        Cue(6.0, 12.5, "Tutorial opens the online learning page in the browser."),
        Cue(12.5, 22.0, "Check for Updates compares the installed version with the latest available version."),
        Cue(22.0, 29.5, "About shows the software version and product information."),
        Cue(29.5, 34.8, "The tutorial page can also be used to find published training videos."),
    ],
    "5. MINGDA SignMaker Creating, Opening, Saving, and Reusing Projects.mp4": [
        Cue(0.5, 7.0, "The project starts with an existing shape on the canvas."),
        Cue(7.0, 13.5, "Create or open another project to replace the current workspace."),
        Cue(13.5, 20.5, "The imported IKEA artwork appears as a new editable shape."),
        Cue(20.5, 27.0, "Home shows recent project cards for quick reuse."),
        Cue(27.0, 36.5, "Opening a saved project restores its artwork and layout."),
        Cue(36.5, 46.5, "Project settings remain available after reopening the file."),
        Cue(46.5, 56.5, "Use Save Project or Save As to store geometry and parameters in an SMP file."),
        Cue(56.5, 71.2, "A saved SMP project can be reused later without rebuilding the job from the original DXF."),
    ],
    "6. MINGDA SignMaker Importing DXF SVG Files and Creating Text.mp4": [
        Cue(0.5, 7.0, "Open File lets you import artwork from the Home page or Project page."),
        Cue(7.0, 18.0, "Choose a DXF or SVG file from the tutorial folder."),
        Cue(18.0, 28.5, "Additional artwork can be imported into the same project."),
        Cue(28.5, 37.0, "After import, check that every object appears inside the printable area."),
        Cue(37.0, 44.5, "The Shape List shows the imported objects separately."),
        Cue(44.5, 50.2, "Use the Text tool to create a text object and add it to the same canvas."),
    ],
    "7.1 MINGDA SignMaker 2D View Navigation.mp4": [
        Cue(0.5, 7.0, "Use zoom controls or the mouse wheel to change the 2D view scale."),
        Cue(7.0, 14.5, "Pan the canvas when the model or bed moves outside the visible area."),
        Cue(14.5, 21.5, "Zoom in to inspect contours and small details."),
        Cue(21.5, 25.8, "Use fit or reset view to return to a full-bed overview."),
    ],
    "7.2 MINGDA SignMaker Printable Area And No-Print Zone.mp4": [
        Cue(0.5, 15.0, "Machine settings define the printable area shown on the canvas."),
        Cue(15.0, 25.0, "Printer profile and bed exclude settings can change the usable bed region."),
        Cue(25.0, 35.5, "Move the shape to check whether it enters a restricted or unsafe area."),
        Cue(35.5, 48.5, "Keep the model inside the valid printable area before processing or export."),
    ],
    "8. MIGNDA SignMaker Shape List and Object Management.mp4": [
        Cue(0.5, 8.0, "A multi-object project is displayed on the canvas and in the Shape List."),
        Cue(8.0, 17.0, "Selecting an item in Shape List selects the matching object on the canvas."),
        Cue(17.0, 26.0, "Multiple shapes can be selected together for combined operations."),
        Cue(26.0, 36.0, "Use the list to switch between separate imported letters or objects."),
        Cue(36.0, 45.5, "Scroll and manage the list when a project contains many shapes."),
        Cue(45.5, 49.8, "Confirm the selected object before changing parameters or deleting anything."),
    ],
    "9. MINGDA SignMaker Basic Shape Editing Move Rotate Scale and Mirror.mp4": [
        Cue(0.5, 15.0, "Select the object and move it on the 2D canvas."),
        Cue(15.0, 31.0, "Use the rotate handle or transform panel to change the object angle."),
        Cue(31.0, 45.0, "Precise transform values let you position and rotate the shape numerically."),
        Cue(45.0, 60.0, "Scale changes the object size; keep proportions locked when needed."),
        Cue(60.0, 75.3, "Mirror tools flip the shape horizontally or vertically for orientation changes."),
    ],
    "10. MINGDA SignMaker Advanced Shape Editing Boolean Group Ungroup Undo and Redo.mp4": [
        Cue(0.5, 15.5, "Two overlapping shapes are selected for Boolean editing."),
        Cue(15.5, 31.0, "Intersection and Difference create new geometry from the selected overlap."),
        Cue(31.0, 45.0, "Undo and Redo let you verify or recover from each editing step."),
        Cue(45.0, 61.0, "Separate objects can be moved and checked after Boolean operations."),
        Cue(61.0, 78.4, "Group, Ungroup, and Explode help manage complex imported logos or letter sets."),
    ],
    "11. MINGDA SignMaker Start Points and Print Order.mp4": [
        Cue(0.5, 12.0, "Select the IKEA lettering before editing path-related settings."),
        Cue(12.0, 22.0, "Zoom in and activate the Start Point tool on the letter outlines."),
        Cue(22.0, 32.0, "Colored markers show where each contour will begin printing."),
        Cue(32.0, 41.0, "Print Order controls the sequence between separate letters or objects."),
        Cue(41.0, 50.4, "After changing start points or order, export G-code only after reprocessing."),
    ],
    "12. MINGDA SignMaker Shell Height-Layer Height-Line Width-Wall Thickness.mp4": [
        Cue(0.5, 17.0, "The Shape tab contains the basic shell and layer parameters."),
        Cue(17.0, 33.0, "Shell Height and Layer Height control the vertical size and layer count."),
        Cue(33.0, 41.0, "Run Process after changing core slicing parameters."),
        Cue(41.0, 57.0, "Preview shows the resulting shell height and wall structure in 3D."),
        Cue(57.0, 81.0, "Changing layer or wall settings changes the visible path density and wall result."),
        Cue(81.0, 100.0, "Line Width and Wall Thickness affect strength, light transmission, and print time."),
        Cue(100.0, 109.8, "Return to Project when another parameter change is needed."),
    ],
    "13. MINGDA SignMaker Creating Straight Beveled and Custom Wall Edges.mp4": [
        Cue(0.5, 17.0, "Start with the R shape and open the wall edge settings."),
        Cue(17.0, 41.0, "Straight Wall creates a vertical sign shell for standard jobs."),
        Cue(41.0, 73.0, "Beveled Wall changes the side wall into a sloped surface."),
        Cue(73.0, 97.0, "Top Small, Top Large, and bevel width change the direction and size of the slope."),
        Cue(97.0, 121.0, "Custom Wall uses preset profiles or imported shapes for special edge designs."),
        Cue(121.0, 140.0, "Compare the final wall edge in 3D Preview before production."),
    ],
    "14. MINGDA SignMaker Bottom Structures and Screw Holes.mp4": [
        Cue(0.5, 25.0, "Open the Bottom settings and start from a simple R-shaped shell."),
        Cue(25.0, 49.0, "Bottom Shell creates a closed or reinforced lower surface."),
        Cue(49.0, 85.0, "Screw-hole settings add mounting holes to compatible bottom structures."),
        Cue(85.0, 121.0, "Process again after each bottom structure change."),
        Cue(121.0, 157.0, "Back Plate Slot and V-Groove create mounting features for the back plate."),
        Cue(157.0, 205.0, "Preview the groove outline and check how it follows the outer and inner contours."),
        Cue(205.0, 241.0, "Bottom edge wrapping and outlining add lower-edge fitting structures."),
        Cue(241.0, 301.0, "LED strip slots reserve space for lighting around the shell."),
        Cue(301.0, 349.0, "Rotate the 3D model to confirm holes, grooves, and slots are correctly placed."),
        Cue(349.0, 412.0, "Some bottom options are mutually exclusive, so verify the final active structure before export."),
    ],
    "15. MINGDA SignMaker Top Structures.mp4": [
        Cue(0.5, 17.0, "Open the Top settings for the R-shaped shell."),
        Cue(17.0, 33.0, "Top Shell creates a closed or reinforced upper surface."),
        Cue(33.0, 57.0, "Preview shows how the top surface closes the letter shape."),
        Cue(57.0, 81.0, "Acrylic Face Slot creates a straight locating slot for the face panel."),
        Cue(81.0, 96.0, "Acrylic Face V-Groove provides a different panel fitting structure."),
    ],
    "16.1 MINGDA SignMaker Anti-Warp Brim.mp4": [
        Cue(0.5, 16.0, "Enable Anti-Warp Brim in the Other settings."),
        Cue(16.0, 31.0, "The brim appears around the outside and can also support inner openings."),
        Cue(31.0, 46.0, "Use 3D Preview to check that the brim is placed around the shell base."),
        Cue(46.0, 61.0, "Adjust height, speed, and breakaway gap to control support and removal."),
        Cue(61.0, 68.0, "Confirm the brim does not interfere with final assembly features."),
    ],
    "16.2 MINGDA SignMaker Letter Bridges.mp4": [
        Cue(0.5, 25.0, "Enable Letter Bridges and review the bridge settings in Other."),
        Cue(25.0, 41.0, "Process the model so the bridge can be generated in the 3D result."),
        Cue(41.0, 65.0, "The green bridge connects separated areas of the letter structure."),
        Cue(65.0, 89.0, "Change bridge type and width to control the visible connection."),
        Cue(89.0, 121.0, "Bridge bevel height and base height control how the bridge blends into the shell."),
        Cue(121.0, 134.5, "Inspect the bridge from several angles before exporting."),
    ],
    "16.3 MINGDA SignMaker DXF Export Compensation.mp4": [
        Cue(0.5, 10.0, "DXF Export Compensation controls panel and back-plate fitting offsets."),
        Cue(10.0, 26.0, "The diagram shows how outer clearance, inner clearance, and laser kerf change the exported contour."),
        Cue(26.0, 41.0, "Enter compensation values before exporting the DXF file."),
        Cue(41.0, 56.0, "Export the adjusted DXF and confirm overwrite prompts when needed."),
        Cue(56.0, 64.0, "Use test exports to tune the fit for the material and cutting process."),
    ],
    "17. MINGDA SignMaker Machine Setup and Hardware Settings.mp4": [
        Cue(0.5, 16.0, "The Machine tab controls printer profile and hardware settings."),
        Cue(16.0, 31.0, "Choose the correct printer profile and nozzle configuration."),
        Cue(31.0, 46.0, "Printable area and bed exclude settings change the usable region on the canvas."),
        Cue(46.0, 57.0, "Nozzle, filament, retract, and Z-hop values affect generated toolpaths."),
    ],
    "19.1 MINGDA SignMaker Speed Tempetature Cooling Settings.mp4": [
        Cue(0.5, 20.0, "The Print tab contains speed, temperature, and cooling settings."),
        Cue(20.0, 36.0, "Preview keeps the same model visible while print parameters are adjusted."),
        Cue(36.0, 51.0, "Speed values affect surface quality, travel behavior, and print time."),
        Cue(51.0, 62.0, "Temperature and cooling should be tuned for material, nozzle size, and printer condition."),
    ],
    "19.2 MINGDA SignMaker Color Change-Prime Tower-Start and End Gcode.mp4": [
        Cue(0.5, 21.0, "Enable Color Change and set the height where the material change should occur."),
        Cue(21.0, 49.0, "Macro Index selects the machine-specific command for the color-change action."),
        Cue(49.0, 73.0, "Enable Prime Tower when the nozzle needs purging after a color or material change."),
        Cue(73.0, 97.0, "Set tower position, size, and infill so it stays inside the safe print area."),
        Cue(97.0, 113.0, "Start and End G-code editors expose machine scripts for advanced users."),
        Cue(113.0, 119.0, "Check these settings carefully before exporting G-code."),
    ],
    "20. MINGAD SignMaker Process.mp4": [
        Cue(0.5, 17.0, "Process generates the slicing result from the current geometry and settings."),
        Cue(17.0, 31.0, "If export is attempted before processing, SignMaker prompts you to process first."),
        Cue(31.0, 41.0, "Choose where to save only after the model has a valid processed result."),
        Cue(41.0, 51.0, "After processing, return to the canvas or Preview and check the result."),
    ],
    "21. MINGDA SignMaker 3D Preview.mp4": [
        Cue(0.5, 10.0, "Open Preview to inspect the processed 3D result."),
        Cue(10.0, 21.0, "Rotate the model and check shell height, wall shape, and bottom features."),
        Cue(21.0, 35.5, "Layer or path preview helps verify contours, grooves, and brim paths."),
        Cue(35.5, 44.8, "If the structure is wrong, return to Project, adjust parameters, and process again."),
    ],
    "22. MINGDA SignMaker Export G-code-STL-Back Plate DXF-Acrylic Face DXF.mp4": [
        Cue(0.5, 11.0, "Export G-code after the model has been processed."),
        Cue(11.0, 21.0, "Open the exported result in the slicer or preview tool when needed."),
        Cue(21.0, 36.0, "Export STL for 3D checking, archiving, or a secondary slicing workflow."),
        Cue(36.0, 56.0, "Export Back Plate DXF when the back plate contour is needed for cutting."),
        Cue(56.0, 76.0, "Export Acrylic Face DXF for the face panel outline."),
        Cue(76.0, 86.7, "Confirm overwrite prompts and verify the saved files in the target folder."),
    ],
    "23.1 MINGDA SignMaker Decorative Face Panel Patterns.mp4": [
        Cue(0.5, 13.0, "In SignMaker, enable the closed shell structure needed for the decorative panel workflow."),
        Cue(13.0, 21.0, "Export STL and import it into MINGDA OrcaSlicer."),
        Cue(21.0, 37.0, "In OrcaSlicer, adjust shell and infill settings for the decorative surface."),
        Cue(37.0, 46.0, "Slice preview reveals the actual infill pattern on the panel surface."),
        Cue(46.0, 56.0, "Change the infill pattern to compare different decorative textures."),
        Cue(56.0, 62.5, "The final decorative look comes from OrcaSlicer infill, not from SignMaker alone."),
    ],
    "23.2 MINGDA SignMaker Grid Fill and Solid Letters.mp4": [
        Cue(0.5, 17.0, "In SignMaker, use Top Shell settings to prepare a solid-letter STL."),
        Cue(17.0, 33.0, "Export the STL and load it into MINGDA OrcaSlicer."),
        Cue(33.0, 57.0, "Set top, bottom, wall, and infill parameters for the solid or grid-fill result."),
        Cue(57.0, 81.0, "Slice preview shows the grid or fill pattern inside the letter."),
        Cue(81.0, 102.0, "Tune infill and overhang-related options until the preview paths are printable."),
    ],
    "24. MINGDA SignMaker Common FAQ and Pitfalls.mp4": [
        Cue(0.5, 49.0, "Artwork and machine setup problems usually come from wrong units, printer profile, or compensation values."),
        Cue(49.0, 85.0, "If G-code or STL cannot export, check whether parameters changed after the last Process operation."),
        Cue(85.0, 121.0, "If color change or print order looks wrong, export G-code after setting the correct height, macro, start point, and order."),
        Cue(121.0, 158.0, "Bottom and screw-hole issues usually mean the selected bottom mode does not support the requested feature."),
        Cue(158.0, 189.5, "Wall, Top, and Bottom sub-options can be mutually exclusive, so verify the active structure before production."),
    ],
}


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def srt_time(seconds: float) -> str:
    millis = int(round(max(0.0, seconds) * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def srt_name(index: int, video: str) -> str:
    stem = Path(video).stem
    slug = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").lower()
    return f"{index:02}_{slug[:70]}.srt"


def write_srt(path: Path, cues: list[Cue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for idx, cue in enumerate(cues, start=1):
            handle.write(f"{idx}\n")
            handle.write(f"{srt_time(cue.start)} --> {srt_time(cue.end)}\n")
            handle.write(f"{cue.text}\n\n")


def burn_video(ffmpeg: str, input_video: Path, srt_rel: str, output_video: Path, working_dir: Path, overwrite: bool) -> None:
    if output_video.exists() and not overwrite:
        return
    output_video.parent.mkdir(parents=True, exist_ok=True)
    style = (
        "FontName=Arial,"
        "FontSize=16,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BackColour=&H90000000,"
        "BorderStyle=3,"
        "Outline=1,"
        "Shadow=0,"
        "Alignment=2,"
        "MarginV=30"
    )
    vf = f"subtitles='{srt_rel}':force_style='{style}'"
    command = [
        ffmpeg,
        "-y" if overwrite else "-n",
        "-i",
        str(input_video),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(output_video),
    ]
    result = subprocess.run(command, cwd=working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"Failed to burn subtitles for {input_video.name}\n{result.stderr[-3000:]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--only", action="append", help="Process only files containing this text.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    videos = sorted(args.input_dir.glob("*.mp4"), key=natural_key)
    if args.only:
        needles = [item.lower() for item in args.only]
        videos = [video for video in videos if any(needle in video.name.lower() for needle in needles)]

    missing = [video.name for video in videos if video.name not in SUBTITLES]
    if missing:
        raise SystemExit("Missing content subtitles for:\n" + "\n".join(missing))

    subtitle_dir = args.output_dir / "subtitles"
    hard_dir = args.output_dir / "videos"
    for index, video in enumerate(videos, start=1):
        srt_file = subtitle_dir / srt_name(index, video.name)
        write_srt(srt_file, SUBTITLES[video.name])
        rel_srt = srt_file.relative_to(args.output_dir).as_posix()
        output_video = hard_dir / f"{video.stem} - content hard subtitles.mp4"
        print(f"[{index}/{len(videos)}] {video.name}")
        burn_video(ffmpeg, video, rel_srt, output_video, args.output_dir, args.overwrite)

    print(f"Done. Output: {args.output_dir}")


if __name__ == "__main__":
    main()
