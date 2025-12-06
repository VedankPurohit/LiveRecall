"""
LiveRecall - Streamlit UI
Uses FastAPI backend for all operations
"""
import streamlit as st
import requests
from pathlib import Path
import time

# API base URL
API_BASE = "http://localhost:8742/api/v1"

st.set_page_config(page_title="LiveRecall", page_icon="🧠", layout="wide")


def api_get(endpoint: str) -> dict:
    """Make GET request to API"""
    try:
        response = requests.get(f"{API_BASE}{endpoint}", timeout=30)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to API. Is the server running?"}
    except Exception as e:
        return {"error": str(e)}


def api_post(endpoint: str, data: dict = None) -> dict:
    """Make POST request to API"""
    try:
        response = requests.post(f"{API_BASE}{endpoint}", json=data, timeout=60)
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to API. Is the server running?"}
    except Exception as e:
        return {"error": str(e)}


def check_api_connection() -> bool:
    """Check if API is reachable"""
    result = api_get("/health")
    return "error" not in result


# --- Check API Connection ---
api_connected = check_api_connection()

if not api_connected:
    st.error("⚠️ Cannot connect to API server!")
    st.info("Start the API server first:")
    st.code("uv run uvicorn api.main:app --port 8742")
    st.stop()


# --- Sidebar ---
with st.sidebar:
    st.header("🧠 LiveRecall")

    # Get status from API
    status = api_get("/status")

    if "error" in status:
        st.error(status["error"])
    else:
        # Database stats
        db_stats = status.get("database", {})
        st.metric("Total Screenshots", db_stats.get("total_screenshots", 0))
        st.metric("Synced", db_stats.get("synced", 0))
        st.metric("Unsynced", db_stats.get("unsynced", 0))

        st.divider()

        # Recording status
        recording = status.get("recording", {})
        if recording.get("is_recording"):
            st.success("● Recording")
        else:
            st.info("○ Not Recording")

        # Model status
        model = status.get("model", {})
        if model.get("loaded"):
            st.success(f"🧠 Model loaded ({model.get('device')})")
            idle = model.get("idle_seconds", 0)
            st.caption(f"Idle: {idle:.0f}s")
        else:
            st.info("🧠 Model not loaded")

        st.divider()

        # Unload model button
        if model.get("loaded"):
            if st.button("Unload Model"):
                result = api_post("/sync/model/unload")
                if result.get("success"):
                    st.success("Model unloaded")
                    st.rerun()


# --- Main tabs ---
tab1, tab2, tab3 = st.tabs(["🔍 Search", "🗑️ Delete", "⚙️ Settings"])

# =============================================================================
# SEARCH TAB
# =============================================================================
with tab1:
    st.title("Search Your Memory")

    # Get current status
    status = api_get("/status")
    recording_status = status.get("recording", {})
    db_stats = status.get("database", {})

    # Control buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("▶️ Start Recording", disabled=recording_status.get("is_recording", False)):
            result = api_post("/recording/start")
            if result.get("success"):
                st.success("Recording started!")
            else:
                st.error(result.get("message", "Failed to start"))
            st.rerun()

    with col2:
        if st.button("⏹️ Stop Recording", disabled=not recording_status.get("is_recording", False)):
            result = api_post("/recording/stop")
            if result.get("success"):
                st.success("Recording stopped!")
            else:
                st.error(result.get("message", "Failed to stop"))
            st.rerun()

    with col3:
        unsynced = db_stats.get("unsynced", 0)
        if st.button(f"🔄 Sync ({unsynced})", disabled=unsynced == 0):
            with st.spinner(f"Syncing {unsynced} screenshots..."):
                result = api_post("/sync/start", {"batch_size": 10})

                if result.get("success"):
                    # Poll for completion
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    while True:
                        sync_status = api_get("/sync/status")
                        if not sync_status.get("is_syncing", False):
                            break

                        total = sync_status.get("total", 1)
                        processed = sync_status.get("processed", 0)
                        progress = processed / total if total > 0 else 0
                        progress_bar.progress(progress)
                        status_text.text(f"Processing {processed}/{total}...")
                        time.sleep(0.5)

                    st.success("Sync complete!")
                else:
                    st.error(result.get("message", "Sync failed"))
            st.rerun()

    with col4:
        safe_mode = st.toggle("Safe Mode", value=True)

    # Safe mode level
    if safe_mode:
        safe_mode_level = st.selectbox(
            "Moderation Level",
            options=["low", "lowmid", "mid", "midhigh", "high", "veryhigh", "extreme"],
            index=2,
            format_func=lambda x: x.replace("mid", "Mid").replace("low", "Low").replace("high", "High").replace("very", "Very ").replace("extreme", "Extreme").title()
        )
    else:
        safe_mode_level = "mid"

    # Search input
    col_search, col_advanced = st.columns([2, 1])

    with col_search:
        search_term = st.text_input("🔍 Search", placeholder="What are you looking for?")

    with col_advanced:
        with st.expander("Advanced Options"):
            negative_texts = st.text_input(
                "Negative terms",
                placeholder="Terms to avoid, comma separated"
            )
            negative_weight = st.slider("Negative weight", 0.0, 2.0, 1.0, 0.1)
            result_limit = st.slider("Max results", 10, 100, 20, 10)

    # Search button
    if st.button("🔍 Search", type="primary"):
        if not search_term:
            st.warning("Please enter a search term")
        elif db_stats.get("synced", 0) == 0:
            st.warning("No synced screenshots yet. Click 'Sync' first!")
        else:
            with st.spinner("Searching..."):
                # Build search request
                search_data = {
                    "query": search_term,
                    "limit": result_limit,
                    "safe_mode": safe_mode,
                    "safe_mode_level": safe_mode_level,
                }

                if negative_texts and not safe_mode:
                    search_data["negative_texts"] = [t.strip() for t in negative_texts.split(",") if t.strip()]
                    search_data["negative_weight"] = negative_weight

                # Call API
                result = api_post("/search", search_data)

            if "error" in result:
                st.error(result.get("error") or result.get("detail", "Search failed"))
            elif "detail" in result:
                st.error(result["detail"])
            elif result.get("total_results", 0) == 0:
                st.warning("No results found. Try a different search term.")
            else:
                st.success(f"Found {result['total_results']} results!")

                results = result.get("results", [])

                # Image slider
                if len(results) > 1:
                    selected_idx = st.slider(
                        "Browse results",
                        0, len(results) - 1, 0
                    )
                else:
                    selected_idx = 0

                # Show selected image
                selected = results[selected_idx]
                image_url = f"http://localhost:8742{selected['image_url']}"

                st.image(image_url, use_column_width=True)
                st.caption(f"Image {selected_idx + 1} of {len(results)} • Similarity: {selected['similarity']:.2%}")

                # Gallery
                st.subheader("Gallery")
                cols = st.columns(4)
                for i, r in enumerate(results):
                    with cols[i % 4]:
                        img_url = f"http://localhost:8742{r['image_url']}"
                        st.image(img_url, use_column_width=True)
                        st.caption(f"{r['similarity']:.1%}")

# =============================================================================
# DELETE TAB
# =============================================================================
with tab2:
    st.title("Delete Screenshots")

    status = api_get("/status")
    db_stats = status.get("database", {})
    total = db_stats.get("total_screenshots", 0)

    st.write(f"Total screenshots: {total}")

    if total > 0:
        st.warning("⚠️ This will permanently delete all screenshots!")

        confirm = st.checkbox("I understand this will delete ALL screenshots permanently")

        if st.button("🗑️ Clear All Data", type="secondary", disabled=not confirm):
            result = requests.delete(
                f"{API_BASE}/screenshots",
                params={"confirm": True, "delete_files": True}
            ).json()

            if result.get("success"):
                st.success(f"Deleted {result.get('deleted_count', 0)} screenshots!")
                st.rerun()
            else:
                st.error("Failed to delete")
    else:
        st.info("No screenshots to delete")

# =============================================================================
# SETTINGS TAB
# =============================================================================
with tab3:
    st.title("Settings")

    # Get current config
    config = api_get("/config")

    if "error" in config:
        st.error(config["error"])
    else:
        st.subheader("Capture Mode")

        mode_descriptions = {
            "normal": "Balanced settings for everyday use",
            "games": "Less frequent captures for gaming sessions",
            "fast": "Higher sensitivity to capture more details",
            "presentation": "Optimized for slide decks and presentations",
            "video": "Captures key scenes and transitions in videos",
            "coding": "Tracks meaningful changes in code editors",
            "security": "Minimizes false triggers for surveillance",
            "timelapse": "Regular interval captures regardless of content",
        }

        capture_config = config.get("capture", {})
        current_mode = capture_config.get("mode", "normal")

        selected_mode = st.selectbox(
            "Capture Mode",
            options=list(mode_descriptions.keys()),
            index=list(mode_descriptions.keys()).index(current_mode) if current_mode in mode_descriptions else 0,
            format_func=lambda x: x.title()
        )

        st.info(mode_descriptions.get(selected_mode, ""))

        if selected_mode != current_mode:
            if st.button("Apply Mode"):
                result = api_post(f"/recording/mode/{selected_mode}")
                st.success(f"Mode changed to {selected_mode}")
                st.rerun()

        st.divider()

        st.subheader("Capture Settings")
        col1, col2, col3 = st.columns(3)

        with col1:
            new_interval = st.number_input(
                "Interval (seconds)",
                min_value=0.5,
                max_value=60.0,
                value=float(capture_config.get("interval", 2.0)),
                step=0.5
            )

        with col2:
            new_threshold = st.slider(
                "Change Threshold",
                min_value=0.5,
                max_value=0.99,
                value=float(capture_config.get("threshold", 0.9)),
                step=0.01,
                help="Higher = less sensitive (fewer captures)"
            )

        with col3:
            new_quality = st.slider(
                "Image Quality",
                min_value=50,
                max_value=100,
                value=int(capture_config.get("quality", 95)),
                step=5,
                help="JPEG quality (higher = better quality, larger files)"
            )

        if st.button("Save Capture Settings"):
            result = requests.put(
                f"{API_BASE}/config",
                json={
                    "capture_interval": new_interval,
                    "capture_threshold": new_threshold,
                    "capture_quality": new_quality,
                }
            ).json()

            if result.get("success"):
                st.success("Settings saved!")
            else:
                st.error("Failed to save settings")

        st.divider()

        st.subheader("Model Settings")

        auto_unload = config.get("auto_unload_seconds", 300)
        new_auto_unload = st.number_input(
            "Auto-unload timeout (seconds)",
            min_value=0,
            max_value=3600,
            value=auto_unload,
            step=60,
            help="0 = never auto-unload"
        )

        if st.button("Save Model Settings"):
            result = requests.put(
                f"{API_BASE}/config",
                json={"auto_unload_seconds": new_auto_unload}
            ).json()

            if result.get("success"):
                st.success("Settings saved!")
            else:
                st.error("Failed to save settings")

        st.divider()

        st.subheader("Storage Management")

        # Get compression config and stats
        compression_config = config.get("compression", {})
        compression_stats = api_get("/compression/stats")

        # Show storage location
        status = api_get("/status")
        st.caption(f"📁 {status.get('data_directory', 'Unknown')}")

        # Compression toggle
        compress_enabled = st.toggle(
            "Auto-compress old screenshots",
            value=compression_config.get("enabled", False),
            help="Automatically compress screenshots older than the specified days"
        )

        if compress_enabled:
            col1, col2 = st.columns(2)

            with col1:
                compress_after_days = st.number_input(
                    "Compress after (days)",
                    min_value=7,
                    max_value=365,
                    value=compression_config.get("after_days", 60),
                    step=7,
                    help="Screenshots older than this will be compressed"
                )

            with col2:
                compress_quality = st.slider(
                    "Compression quality",
                    min_value=50,
                    max_value=90,
                    value=compression_config.get("quality", 85),
                    step=5,
                    help="Lower = smaller files, more quality loss"
                )

            if st.button("Save Compression Settings"):
                result = requests.put(
                    f"{API_BASE}/config",
                    json={
                        "compression_enabled": compress_enabled,
                        "compression_after_days": compress_after_days,
                        "compression_quality": compress_quality,
                    }
                ).json()

                if result.get("success"):
                    st.success("Compression settings saved!")
                else:
                    st.error("Failed to save settings")

        # Show compression stats
        if "error" not in compression_stats:
            compressed = compression_stats.get("compressed_count", 0)
            compressible = compression_stats.get("compressible_count", 0)
            original_bytes = compression_stats.get("original_size_bytes", 0)

            st.caption(f"📊 {compressed} screenshots compressed")

            if compressible > 0:
                st.info(f"💡 {compressible} screenshots can be compressed")

                # Manual compress button
                if st.button(f"🗜️ Compress Now ({compressible})"):
                    with st.spinner(f"Compressing {compressible} screenshots..."):
                        result = api_post("/compression/start")

                        if result.get("success"):
                            # Poll for completion
                            progress_bar = st.progress(0)
                            status_text = st.empty()

                            while True:
                                comp_status = api_get("/compression/status")
                                if not comp_status.get("is_compressing", False):
                                    break

                                total = comp_status.get("total", 1)
                                processed = comp_status.get("processed", 0)
                                progress = processed / total if total > 0 else 0
                                progress_bar.progress(progress)
                                saved_kb = comp_status.get("bytes_saved", 0) // 1024
                                status_text.text(f"Compressing {processed}/{total}... ({saved_kb}KB saved)")
                                time.sleep(0.5)

                            final_saved = comp_status.get("bytes_saved", 0)
                            st.success(f"Compression complete! Saved {final_saved // 1024}KB")
                        else:
                            st.error(result.get("message", "Compression failed"))
                    st.rerun()

            if original_bytes > 0:
                saved_mb = original_bytes / (1024 * 1024)
                st.caption(f"💾 Original size of compressed images: {saved_mb:.1f}MB")
