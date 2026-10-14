import os
import re
import math
import subprocess
import zipfile
from typing import Callable, Optional, List, Dict
import imageio_ffmpeg


def get_ffmpeg_binary() -> str:
    """Returns the path to the ffmpeg executable."""
    return imageio_ffmpeg.get_ffmpeg_exe()


def get_video_info(video_path: str) -> Dict[str, any]:
    """
    Extracts video duration and basic metadata using ffmpeg stderr output.
    Returns a dict with 'duration' (seconds), 'formatted_duration', 'resolution', etc.
    """
    ffmpeg_exe = get_ffmpeg_binary()
    cmd = [ffmpeg_exe, "-i", video_path]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stderr = process.stderr

    duration_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if not duration_match:
        raise ValueError("Could not determine video duration. The file may be invalid or corrupted.")

    hours = int(duration_match.group(1))
    minutes = int(duration_match.group(2))
    seconds = float(duration_match.group(3))
    total_seconds = (hours * 3600) + (minutes * 60) + seconds

    # Try to extract resolution (e.g. 1920x1080)
    res_match = re.search(r",\s*(\d{2,5})x(\d{2,5})", stderr)
    resolution = f"{res_match.group(1)}x{res_match.group(2)}" if res_match else "Unknown"

    # Check if video has an audio stream
    has_audio = "Audio:" in stderr

    return {
        "duration": total_seconds,
        "formatted_duration": f"{hours:02d}:{minutes:02d}:{seconds:05.2f}",
        "resolution": resolution,
        "has_audio": has_audio,
    }


class ChunkResult:
    """
    Result container holding generated video chunks and optional audio chunks.
    Maintains list-like behavior for backward compatibility.
    """
    def __init__(self, video_chunks: List[str], audio_chunks: Optional[List[str]] = None):
        self.video_chunks = video_chunks
        self.audio_chunks = audio_chunks or []

    def __iter__(self):
        return iter(self.video_chunks)

    def __len__(self):
        return len(self.video_chunks)

    def __getitem__(self, idx):
        return self.video_chunks[idx]

    @property
    def all_files(self) -> List[str]:
        return self.video_chunks + self.audio_chunks


def chunk_video(
    video_path: str,
    output_dir: str,
    chunk_duration: float = 30.0,
    naming_pattern: str = "scene {n}.mp4",
    accurate_cut: bool = False,
    strip_audio: bool = False,
    extract_audio: bool = False,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    start_callback: Optional[Callable[[int, int, str], None]] = None,
    **kwargs,
) -> ChunkResult:
    """
    Splits the given video file into chunks of `chunk_duration` seconds each.
    
    Parameters:
        video_path: Path to the input video.
        output_dir: Directory where output chunks will be stored.
        chunk_duration: Duration of each chunk in seconds (default: 30.0).
        naming_pattern: Filename template, e.g., 'scene {n}.mp4' or 'scene_{n}.mp4'.
        accurate_cut: If True, re-encodes video for frame-accurate cuts.
                      If False, uses stream copy for lightning-fast lossless cutting.
        strip_audio: If True, removes audio track from the video files (muted video).
        extract_audio: If True, saves separate audio files (e.g. 'scene 1 audio.mp3').
        progress_callback: Optional callback(chunk_index, total_chunks, output_filename) on completion.
        start_callback: Optional callback(chunk_index, total_chunks, output_filename) on chunk start.

    Returns:
        ChunkResult with .video_chunks and .audio_chunks.
    """
    os.makedirs(output_dir, exist_ok=True)
    ffmpeg_exe = get_ffmpeg_binary()

    info = get_video_info(video_path)
    total_duration = info["duration"]

    if total_duration <= 0:
        raise ValueError("Video duration is 0 or invalid.")

    total_chunks = math.ceil(total_duration / chunk_duration)
    output_files = []
    output_audio_files = []

    for i in range(1, total_chunks + 1):
        start_time = (i - 1) * chunk_duration
        current_chunk_duration = min(chunk_duration, total_duration - start_time)

        output_filename = naming_pattern.format(n=i)
        output_path = os.path.join(output_dir, output_filename)

        if start_callback:
            start_callback(i, total_chunks, output_path)

        # 1. Produce video chunk
        if accurate_cut:
            cmd = [
                ffmpeg_exe,
                "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(current_chunk_duration),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "22",
            ]
            if strip_audio:
                cmd.append("-an")
            else:
                cmd.extend(["-c:a", "aac"])
            cmd.append(output_path)
        else:
            cmd = [
                ffmpeg_exe,
                "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(current_chunk_duration),
            ]
            if strip_audio:
                cmd.extend(["-c:v", "copy", "-an"])
            else:
                cmd.extend(["-c", "copy"])
            cmd.extend(["-avoid_negative_ts", "make_zero", output_path])

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            if not accurate_cut:
                fallback_cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-ss", str(start_time),
                    "-i", video_path,
                    "-t", str(current_chunk_duration),
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                ]
                if strip_audio:
                    fallback_cmd.append("-an")
                else:
                    fallback_cmd.extend(["-c:a", "aac"])
                fallback_cmd.append(output_path)
                res_fallback = subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res_fallback.returncode != 0:
                    raise RuntimeError(f"FFmpeg error processing chunk {i}: {res_fallback.stderr}")
            else:
                raise RuntimeError(f"FFmpeg error processing chunk {i}: {res.stderr}")

        output_files.append(output_path)

        # 2. Extract separate audio file if requested
        if extract_audio and info.get("has_audio", True):
            base_name, _ = os.path.splitext(output_filename)
            sep = "_" if "_" in base_name else " "
            audio_filename = f"{base_name}{sep}audio.mp3"
            audio_path = os.path.join(output_dir, audio_filename)

            audio_cmd = [
                ffmpeg_exe,
                "-y",
                "-ss", str(start_time),
                "-i", video_path,
                "-t", str(current_chunk_duration),
                "-vn",
                "-c:a", "libmp3lame",
                "-q:a", "2",
                audio_path
            ]
            res_audio = subprocess.run(audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res_audio.returncode != 0:
                # Fallback if libmp3lame isn't available
                fallback_audio_cmd = [
                    ffmpeg_exe,
                    "-y",
                    "-ss", str(start_time),
                    "-i", video_path,
                    "-t", str(current_chunk_duration),
                    "-vn",
                    audio_path
                ]
                subprocess.run(fallback_audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if os.path.exists(audio_path):
                output_audio_files.append(audio_path)

        if progress_callback:
            progress_callback(i, total_chunks, output_path)

    return ChunkResult(output_files, output_audio_files)


def create_zip_archive(files: List[str], zip_output_path: str) -> str:
    """Creates a zip archive containing all specified files."""
    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            if os.path.exists(file):
                zipf.write(file, arcname=os.path.basename(file))
    return zip_output_path
