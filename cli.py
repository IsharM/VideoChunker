import argparse
import os
import sys
from chunker import chunk_video, get_video_info


def main():
    parser = argparse.ArgumentParser(
        description="Split a video into 30-second (or custom duration) chunks named 'scene 1.mp4', 'scene 2.mp4', etc."
    )
    parser.add_argument("video_path", help="Path to input video file")
    parser.add_argument(
        "--chunk-duration",
        "-d",
        type=float,
        default=30.0,
        help="Duration of each chunk in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="output_scenes",
        help="Folder to save scene chunks into (default: output_scenes)",
    )
    parser.add_argument(
        "--pattern",
        "-p",
        default="scene {n}.mp4",
        help="Naming pattern for scenes (default: 'scene {n}.mp4')",
    )
    parser.add_argument(
        "--accurate",
        action="store_true",
        help="Enable frame-accurate re-encoding (slower, but exact keyframe boundaries)",
    )
    parser.add_argument(
        "--strip-audio",
        "--mute",
        action="store_true",
        help="Mute/remove audio stream from output video chunks",
    )
    parser.add_argument(
        "--extract-audio",
        action="store_true",
        help="Extract and save separate audio files (e.g. 'scene 1 audio.mp3')",
    )

    args = parser.parse_args()

    if not os.path.exists(args.video_path):
        print(f"Error: Video file not found: {args.video_path}", file=sys.stderr)
        sys.exit(1)

    print(f"\nAnalyzing video: {args.video_path}")
    try:
        info = get_video_info(args.video_path)
    except Exception as e:
        print(f"Failed to read video information: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Duration: {info['formatted_duration']} ({info['duration']:.2f}s)")
    print(f"Resolution: {info['resolution']}")
    print(f"Chunk Duration: {args.chunk_duration}s")
    print(f"Video Audio: {'Muted / Stripped' if args.strip_audio else 'Kept'}")
    print(f"Separate Audio Files: {'Enabled (MP3)' if args.extract_audio else 'Disabled'}")
    print(f"Output Directory: {os.path.abspath(args.output_dir)}\n")

    def start_cb(idx, total, file_path):
        percent = ((idx - 1) / total) * 100
        bar_len = 25
        filled = int(bar_len * (idx - 1) // total)
        bar = "█" * filled + "░" * (bar_len - filled)
        sys.stdout.write(f"\r[{bar}] {percent:5.1f}% | Splitting: {os.path.basename(file_path)}...")
        sys.stdout.flush()

    def progress_cb(idx, total, file_path):
        percent = (idx / total) * 100
        bar_len = 25
        filled = int(bar_len * idx // total)
        bar = "█" * filled + "░" * (bar_len - filled)
        sys.stdout.write(f"\r[{bar}] {percent:5.1f}% | Completed: {os.path.basename(file_path)}\n")
        sys.stdout.flush()

    try:
        chunk_result = chunk_video(
            video_path=args.video_path,
            output_dir=args.output_dir,
            chunk_duration=args.chunk_duration,
            naming_pattern=args.pattern,
            accurate_cut=args.accurate,
            strip_audio=args.strip_audio,
            extract_audio=args.extract_audio,
            start_callback=start_cb,
            progress_callback=progress_cb,
        )
        print("\n" + "=" * 60)
        print("🎉 CHUNKING COMPLETE!")
        print(f"Total Video Scenes: {len(chunk_result.video_chunks)}")
        if chunk_result.audio_chunks:
            print(f"Total Audio Tracks: {len(chunk_result.audio_chunks)}")
        print(f"Saved To Directory: {os.path.abspath(args.output_dir)}")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\n❌ Error chunking video: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
