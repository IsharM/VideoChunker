import os
import subprocess
from chunker import get_ffmpeg_binary, get_video_info, chunk_video

def test_chunking_pipeline():
    test_dir = "test_output"
    os.makedirs(test_dir, exist_ok=True)
    sample_video = os.path.join(test_dir, "sample_65s.mp4")
    
    ffmpeg_exe = get_ffmpeg_binary()
    print(f"Using FFmpeg binary at: {ffmpeg_exe}")

    # Generate a 65s test video with video testsrc and sine audio
    print("Generating synthetic 65-second test video...")
    gen_cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", "testsrc=duration=65:size=640x360:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:duration=65",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        sample_video
    ]
    subprocess.run(gen_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    info = get_video_info(sample_video)
    print(f"Sample Video Duration: {info['duration']}s, Formatted: {info['formatted_duration']}, Res: {info['resolution']}")
    assert abs(info['duration'] - 65.0) < 1.0, f"Expected ~65s, got {info['duration']}"

    output_scenes_dir = os.path.join(test_dir, "scenes")
    print("\nSplitting into 30s chunks...")
    chunks = chunk_video(
        video_path=sample_video,
        output_dir=output_scenes_dir,
        chunk_duration=30.0,
        naming_pattern="scene {n}.mp4",
        accurate_cut=False,
    )

    print(f"Generated {len(chunks)} chunks:")
    for c in chunks:
        c_info = get_video_info(c)
        print(f" - {os.path.basename(c)}: {c_info['formatted_duration']} ({c_info['duration']:.2f}s)")

    # 65s split into 30s chunks should produce 3 scenes: 30s, 30s, 5s
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
    assert os.path.basename(chunks[0]) == "scene 1.mp4"
    assert os.path.basename(chunks[1]) == "scene 2.mp4"
    assert os.path.basename(chunks[2]) == "scene 3.mp4"

    print("\nAll verification tests passed successfully!")

if __name__ == "__main__":
    test_chunking_pipeline()
