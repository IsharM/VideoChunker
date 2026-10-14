import os
import shutil
import tempfile
import time
import importlib
import streamlit as st
import chunker
importlib.reload(chunker)
from chunker import chunk_video, get_video_info, create_zip_archive

st.set_page_config(
    page_title="Video Chunker - 30s Scene Splitter",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom modern CSS styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FF4B4B 0%, #FF8533 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #888888;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .scene-title {
        font-weight: 600;
        font-size: 1.05rem;
        margin-top: 8px;
        margin-bottom: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🎬 Video Chunker Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Upload a video to split it into 30-second clips saved as scene 1, scene 2, etc.</div>', unsafe_allow_html=True)

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Splitter Settings")
    chunk_sec = st.number_input(
        "Chunk Duration (seconds)",
        min_value=5.0,
        max_value=600.0,
        value=30.0,
        step=5.0,
        help="Default is 30 seconds as requested."
    )
    
    naming_choice = st.selectbox(
        "File Naming Format",
        options=[
            "scene {n}.mp4",
            "scene_{n}.mp4",
            "Scene {n}.mp4",
            "clip_{n:02d}.mp4"
        ],
        index=0,
        help="Output naming pattern. {n} will be replaced by 1, 2, 3..."
    )
    
    accurate_mode = st.toggle(
        "Accurate Frame Cuts (Re-encode)",
        value=False,
        help="Off = Fast stream copy (instant, lossless).\nOn = Re-encodes video so cuts happen exactly on target seconds."
    )
    
    extract_audio_opt = st.toggle(
        "🎵 Strip & Save Audio Separately",
        value=False,
        help="Extracts the audio track from each scene and saves it as a separate audio file (e.g. 'scene 1 audio.mp3', 'scene 2 audio.mp3')."
    )

    strip_video_audio_opt = st.toggle(
        "🔇 Mute Video Clips (Silent Video)",
        value=False,
        help="If enabled, removes audio from the video files so the video clips are silent."
    )
    
    output_dir = st.text_input(
        "Local Output Folder",
        value=os.path.abspath("output_scenes"),
        help="Local directory where the scene clips will be saved."
    )

# Upload Area
uploaded_file = st.file_uploader(
    "Choose a video file to upload",
    type=["mp4", "mov", "avi", "mkv", "webm", "m4v"],
    help="Supports all major video formats."
)

if uploaded_file is not None:
    # Save uploaded file to a temporary location
    temp_dir = tempfile.mkdtemp(prefix="video_chunker_")
    input_file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(input_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Reset state if a different file is uploaded
    if st.session_state.get("current_video_name") != uploaded_file.name:
        st.session_state["current_video_name"] = uploaded_file.name
        st.session_state["chunking_completed"] = False
        st.session_state["processed_chunks"] = []
        st.session_state["audio_chunks"] = []
        st.session_state["zip_path"] = None

    try:
        info = get_video_info(input_file_path)
        total_duration = info["duration"]
        expected_chunks = int(-(-total_duration // chunk_sec))

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("📹 Original Video Preview")
            st.video(input_file_path)

        with col2:
            st.subheader("📊 Video Details")
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                st.metric("Total Duration", info["formatted_duration"])
            with m_col2:
                st.metric("Resolution", info["resolution"])
            with m_col3:
                st.metric("Estimated Scenes", f"{expected_chunks}")

            st.write(f"**Selected Chunk Size:** {chunk_sec:.1f} seconds")
            st.write(f"**Naming Template:** `{naming_choice.format(n=1)}`, `{naming_choice.format(n=2)}`, ...")
            if extract_audio_opt:
                sep_sample = "_" if "_" in naming_choice else " "
                st.write(f"**Separate Audio:** Enabled (`scene{sep_sample}1{sep_sample}audio.mp3`)")
            if strip_video_audio_opt:
                st.write("**Video Audio:** Muted (Silent clips)")
            st.write(f"**Output Directory:** `{output_dir}`")

            start_split = st.button("🚀 Start Splitting Video", type="primary", use_container_width=True)

        if start_split:
            st.markdown("---")
            st.subheader("⚡ Chunking in Progress...")
            progress_bar = st.progress(0.0, text="Initializing video splitting...")
            status_container = st.empty()

            def on_start(idx, total, file_path):
                prog = (idx - 1) / total
                file_name = os.path.basename(file_path)
                progress_bar.progress(
                    prog,
                    text=f"✂️ Slicing Scene {idx} of {total}: {file_name} ({int(prog * 100)}%)"
                )
                status_container.info(f"⏳ Processing **Scene {idx}/{total}**: `{file_name}`...")

            def on_progress(idx, total, file_path):
                prog = idx / total
                file_name = os.path.basename(file_path)
                progress_bar.progress(
                    prog,
                    text=f"✅ Saved Scene {idx} of {total}: {file_name} ({int(prog * 100)}%)"
                )
                status_container.success(f"✔️ Finished **Scene {idx}/{total}**: `{file_name}`")

            start_time = time.time()
            try:
                chunk_result = chunk_video(
                    video_path=input_file_path,
                    output_dir=output_dir,
                    chunk_duration=chunk_sec,
                    naming_pattern=naming_choice,
                    accurate_cut=accurate_mode,
                    strip_audio=strip_video_audio_opt,
                    extract_audio=extract_audio_opt,
                    start_callback=on_start,
                    progress_callback=on_progress,
                )

                chunk_files = chunk_result.video_chunks
                audio_files = chunk_result.audio_chunks
                all_files = chunk_result.all_files

                elapsed_seconds = round(time.time() - start_time, 2)
                progress_bar.progress(1.0, text=f"🎉 100% Complete - All {len(chunk_files)} scenes generated!")

                # Create ZIP archive with all generated files (both video and audio)
                zip_path = os.path.join(output_dir, "all_scenes.zip")
                create_zip_archive(all_files, zip_path)

                # Persist completed state in session
                st.session_state["processed_chunks"] = chunk_files
                st.session_state["audio_chunks"] = audio_files
                st.session_state["output_dir"] = output_dir
                st.session_state["zip_path"] = zip_path
                st.session_state["chunking_completed"] = True
                st.session_state["elapsed_time"] = elapsed_seconds
                st.session_state["chunk_count"] = len(chunk_files)

                st.balloons()
            except Exception as e:
                st.error(f"❌ Error during chunking: {str(e)}")

        # Display results and completion message if chunking is completed
        if st.session_state.get("chunking_completed") and st.session_state.get("processed_chunks"):
            chunks = st.session_state["processed_chunks"]
            audio_chunks = st.session_state.get("audio_chunks", [])
            zip_file = st.session_state.get("zip_path")
            elapsed = st.session_state.get("elapsed_time", "N/A")
            out_folder = st.session_state.get("output_dir", output_dir)

            st.markdown("---")
            
            # Persistent 100% progress indicator
            st.progress(1.0, text=f"✅ 100% Complete — All {len(chunks)} scenes ready!")

            # Prominent Complete Message Banner
            extra_audio_note = f" and **{len(audio_chunks)} audio tracks**" if audio_chunks else ""
            st.success(
                f"### 🎉 Chunking Complete!\n"
                f"Successfully created **{len(chunks)} video scenes**{extra_audio_note} in `{out_folder}` (finished in {elapsed}s)."
            )

            st.subheader(f"🎞️ Generated Scenes ({len(chunks)})")
            
            top_action_col1, top_action_col2 = st.columns([1, 1])
            with top_action_col1:
                st.info(f"📂 Saved locally at: `{out_folder}`")
            with top_action_col2:
                if zip_file and os.path.exists(zip_file):
                    with open(zip_file, "rb") as zf:
                        st.download_button(
                            label="📦 Download All (ZIP - Videos & Audio)",
                            data=zf.read(),
                            file_name="video_scenes.zip",
                            mime="application/zip",
                            use_container_width=True
                        )

            # Display scenes in a 3-column grid
            grid_cols = 3
            for i in range(0, len(chunks), grid_cols):
                cols = st.columns(grid_cols)
                for j in range(grid_cols):
                    idx = i + j
                    if idx < len(chunks):
                        chunk_path = chunks[idx]
                        file_name = os.path.basename(chunk_path)
                        with cols[j]:
                            st.markdown(f"<div class='scene-title'>🎥 {file_name}</div>", unsafe_allow_html=True)
                            if os.path.exists(chunk_path):
                                st.video(chunk_path)
                                with open(chunk_path, "rb") as cf:
                                    st.download_button(
                                        label=f"⬇️ Video: {file_name}",
                                        data=cf.read(),
                                        file_name=file_name,
                                        mime="video/mp4",
                                        key=f"dl_vid_{idx}",
                                        use_container_width=True
                                    )

                            # If separate audio file was extracted for this scene
                            if audio_chunks and idx < len(audio_chunks):
                                audio_path = audio_chunks[idx]
                                if os.path.exists(audio_path):
                                    audio_name = os.path.basename(audio_path)
                                    st.markdown(f"<div style='font-size:0.9rem; font-weight:600; margin-top:8px;'>🎵 {audio_name}</div>", unsafe_allow_html=True)
                                    st.audio(audio_path)
                                    with open(audio_path, "rb") as af:
                                        st.download_button(
                                            label=f"⬇️ Audio: {audio_name}",
                                            data=af.read(),
                                            file_name=audio_name,
                                            mime="audio/mp3",
                                            key=f"dl_aud_{idx}",
                                            use_container_width=True
                                        )

    except Exception as e:
        st.error(f"Could not read video: {str(e)}")
else:
    st.info("👆 Please upload a video file above to get started.")

    # Demonstration info section
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### ⏱️ Automatic 30s Chunks")
        st.caption("Splits long videos into standard 30-second clips, or any custom duration you choose.")
    with c2:
        st.markdown("### 🏷️ Scene 1, 2, ... Naming")
        st.caption("Automatically names clips sequentially (`scene 1.mp4`, `scene 2.mp4`) for easy organization.")
    with c3:
        st.markdown("### ⚡ Fast Lossless Mode")
        st.caption("Uses stream copy by default for lightning-fast splitting with zero quality degradation.")
