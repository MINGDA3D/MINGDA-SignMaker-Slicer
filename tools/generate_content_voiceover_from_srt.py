"""Generate SRT-synchronized voiceover for hard-subtitled tutorial videos."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

try:
    import imageio_ffmpeg
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing dependency: run `python -m pip install imageio-ffmpeg`.") from exc


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "docs" / "MINGDA SignMaker V0.6.0 Content Subtitles"
INPUT_VIDEO_DIR = CONTENT_DIR / "videos"
SRT_DIR = CONTENT_DIR / "subtitles"
OUTPUT_DIR = ROOT / "docs" / "MINGDA SignMaker V0.6.0 Content Voiceover"


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str


def natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def parse_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def parse_srt(path: Path) -> list[Cue]:
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        index = int(lines[0])
        time_match = re.match(r"(.+?)\s*-->\s*(.+)", lines[1])
        if not time_match:
            continue
        cues.append(Cue(index=index, start=parse_time(time_match.group(1)), end=parse_time(time_match.group(2)), text=" ".join(lines[2:])))
    return cues


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{detail[-3000:]}")
    return result


def probe_duration(ffmpeg: str, path: Path) -> float:
    result = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr + result.stdout)
    if not match:
        raise RuntimeError(f"Could not read duration: {path}")
    return int(match.group(1)) * 3600 + int(match.group(2)) * 60 + float(match.group(3))


def build_atempo(speed: float) -> str:
    if speed <= 1.01:
        return "anull"
    parts: list[float] = []
    remaining = speed
    while remaining > 2.0:
        parts.append(2.0)
        remaining /= 2.0
    parts.append(remaining)
    return ",".join(f"atempo={part:.5f}" for part in parts)


def make_tts_jobs(cues_by_video: dict[str, list[Cue]], cue_wav_dir: Path, overwrite: bool) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    for video_stem, cues in cues_by_video.items():
        for cue in cues:
            out = cue_wav_dir / video_stem / f"{cue.index:03}.wav"
            if overwrite or not out.exists():
                jobs.append({"out": str(out), "text": cue.text})
    return jobs


def generate_windows_tts(jobs: list[dict[str, str]], work_dir: Path, voice: str, rate: int) -> None:
    if not jobs:
        return
    work_dir.mkdir(parents=True, exist_ok=True)
    job_file = work_dir / "tts_jobs.json"
    ps_file = work_dir / "generate_tts.ps1"
    job_file.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")
    ps_file.write_text(
        "\n".join(
            [
                "param([string]$JobFile, [string]$Voice, [int]$Rate)",
                "Add-Type -AssemblyName System.Speech",
                "$jobs = Get-Content -LiteralPath $JobFile -Raw -Encoding UTF8 | ConvertFrom-Json",
                "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer",
                "if ($Voice) { $speaker.SelectVoice($Voice) }",
                "$speaker.Rate = $Rate",
                "$speaker.Volume = 100",
                "foreach ($job in $jobs) {",
                "  $dir = Split-Path -Parent $job.out",
                "  if (!(Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }",
                "  $speaker.SetOutputToWaveFile($job.out)",
                "  $speaker.Speak([string]$job.text) | Out-Null",
                "  $speaker.SetOutputToNull()",
                "}",
                "$speaker.Dispose()",
            ]
        ),
        encoding="utf-8",
    )
    run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_file), str(job_file), voice, str(rate)])


def fit_cue_audio(ffmpeg: str, source: Path, target: Path, target_duration: float, overwrite: bool) -> Path:
    if target.exists() and not overwrite:
        return target
    source_duration = probe_duration(ffmpeg, source)
    max_duration = max(0.45, target_duration)
    speed = source_duration / max_duration
    # If the generated voice is shorter than the cue, leave natural speed and let silence fill the rest.
    audio_filter = build_atempo(speed) if speed > 1.01 else "anull"
    run([ffmpeg, "-y", "-i", str(source), "-filter:a", audio_filter, "-ac", "1", "-ar", "44100", str(target)])
    return target


def mix_aligned_audio(ffmpeg: str, video_stem: str, cues: list[Cue], cue_wav_dir: Path, audio_path: Path, video_duration: float, overwrite: bool) -> None:
    if audio_path.exists() and not overwrite:
        return
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    fit_dir = cue_wav_dir / video_stem
    for zero_based, cue in enumerate(cues):
        source = fit_dir / f"{cue.index:03}.wav"
        fitted = fit_cue_audio(ffmpeg, source, fit_dir / f"{cue.index:03}.fit.wav", cue.end - cue.start - 0.08, overwrite)
        inputs.extend(["-i", str(fitted)])
        delay_ms = int(round(cue.start * 1000))
        filters.append(f"[{zero_based}:a]adelay={delay_ms}:all=1[a{zero_based}]")
        labels.append(f"[a{zero_based}]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,apad,loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    run([ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-t", f"{video_duration:.3f}", "-c:a", "aac", "-b:a", "160k", str(audio_path)])


def mux_voiceover(ffmpeg: str, input_video: Path, audio_path: Path, output_video: Path, overwrite: bool) -> None:
    if output_video.exists() and not overwrite:
        return
    output_video.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(input_video),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "copy",
            "-metadata:s:a:0",
            "language=eng",
            str(output_video),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-video-dir", type=Path, default=INPUT_VIDEO_DIR)
    parser.add_argument("--srt-dir", type=Path, default=SRT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--voice", default="Microsoft Zira Desktop")
    parser.add_argument("--rate", type=int, default=0)
    parser.add_argument("--only", action="append", help="Process only videos containing this text.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    videos = sorted(args.input_video_dir.glob("*content hard subtitles.mp4"), key=natural_key)
    if args.only:
        needles = [item.lower() for item in args.only]
        videos = [video for video in videos if any(needle in video.name.lower() for needle in needles)]
    srts = sorted(args.srt_dir.glob("*.srt"), key=natural_key)
    if len(srts) < len(videos):
        raise SystemExit(f"Not enough SRT files: videos={len(videos)} srts={len(srts)}")

    cue_wav_dir = args.output_dir / "_cue_wavs"
    audio_dir = args.output_dir / "audio"
    video_dir = args.output_dir / "videos"
    work_dir = args.output_dir / "_work"
    for directory in (cue_wav_dir, audio_dir, video_dir, work_dir):
        directory.mkdir(parents=True, exist_ok=True)

    selected: list[tuple[Path, Path, str]] = []
    for video in videos:
        stem = video.stem.replace(" - content hard subtitles", "")
        video_slug = slugify(stem)
        matches = [srt for srt in srts if video_slug[:50] in srt.stem]
        if not matches:
            raise SystemExit(f"Missing SRT for {video.name}")
        selected.append((video, matches[0], stem))

    cues_by_video = {stem: parse_srt(srt) for _, srt, stem in selected}
    jobs = make_tts_jobs(cues_by_video, cue_wav_dir, args.overwrite)
    generate_windows_tts(jobs, work_dir, args.voice, args.rate)

    for index, (video, srt, stem) in enumerate(selected, start=1):
        print(f"[{index}/{len(selected)}] {video.name}")
        cues = cues_by_video[stem]
        duration = probe_duration(ffmpeg, video)
        audio_path = audio_dir / f"{stem}.m4a"
        output_video = video_dir / f"{stem} - content hard subtitles voiceover.mp4"
        mix_aligned_audio(ffmpeg, stem, cues, cue_wav_dir, audio_path, duration, args.overwrite)
        mux_voiceover(ffmpeg, video, audio_path, output_video, args.overwrite)

    print(f"Done. Output: {args.output_dir}")


if __name__ == "__main__":
    main()
