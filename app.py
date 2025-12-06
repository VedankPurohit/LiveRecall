"""
LiveRecall - Streamlit UI
Uses new core/ modules for capture, sync, and search
"""
import streamlit as st
import os
from pathlib import Path

# Import new core modules
from core.config import config, get_screenshots_dir
from core.database import db
from core.capture import capture_service
from core.embeddings import get_text_embedding, get_combined_embedding, get_safe_search_embedding, SAFE_MODE_WEIGHTS
from core.processor import sync_screenshots, SyncProgress

# Legacy encryption (keeping for now)
from Components.Crypt import EncryptDecryptImage

st.set_page_config(page_title="LiveRecall", page_icon="🧠", layout="wide")

# Initialize database connection
if "db_connected" not in st.session_state:
    db.connect()
    st.session_state.db_connected = True

# Temp directory for decrypted images
TEMP_DIR = Path("Temp")
TEMP_DIR.mkdir(exist_ok=True)


def remove_temp_images():
    """Clean up temporary decrypted images"""
    for file in TEMP_DIR.iterdir():
        if file.is_file():
            file.unlink()


def search_images(
    query: str,
    safe_mode: bool = True,
    safe_mode_level: str = "mid",
    negative_texts: str = "",
    negative_weight: float = 1.0,
    limit: int = 50
) -> tuple[list[str], list[float]]:
    """Search for images matching the query"""

    # Generate query embedding
    if safe_mode:
        level_key = safe_mode_level.lower().replace(" ", "")
        embedding = get_safe_search_embedding(query, level_key)
    elif negative_texts:
        neg_list = [t.strip() for t in negative_texts.split(",") if t.strip()]
        embedding = get_combined_embedding(
            base_text=query,
            negative_texts=neg_list,
            negative_weight=negative_weight
        )
    else:
        embedding = get_text_embedding(query)

    # Search database
    results = db.search_similar(embedding, limit=limit)

    image_paths = []
    similarities = []

    for result in results:
        image_paths.append(result["image_path"])
        similarities.append(result["similarity"])

    return image_paths, similarities


# --- Sidebar for key and status ---
with st.sidebar:
    st.header("🧠 LiveRecall")

    # Encryption key
    encryption_key = st.text_input("Encryption Key", type="password", key="encryption_key")
    if encryption_key == "DevMode":
        st.warning("DevMode: No encryption")
    elif encryption_key == "":
        st.info("Enter a key to enable encryption")
    else:
        st.success("Encryption enabled")

    st.divider()

    # Status
    stats = db.get_stats()
    st.metric("Total Screenshots", stats["total_screenshots"])
    st.metric("Synced", stats["synced"])
    st.metric("Unsynced", stats["unsynced"])

    # Recording status
    if capture_service.is_running:
        st.success("● Recording")
    else:
        st.info("○ Not Recording")


# --- Main tabs ---
tab1, tab2, tab3 = st.tabs(["🔍 Search", "🗑️ Delete", "⚙️ Settings"])

# =============================================================================
# SEARCH TAB
# =============================================================================
with tab1:
    st.title("Search Your Memory")

    # Control buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("▶️ Start Recording", disabled=capture_service.is_running):
            capture_service.start()
            st.rerun()

    with col2:
        if st.button("⏹️ Stop Recording", disabled=not capture_service.is_running):
            capture_service.stop()
            st.rerun()

    with col3:
        unsynced = db.get_unsynced_count()
        if st.button(f"🔄 Sync ({unsynced})", disabled=unsynced == 0):
            with st.spinner(f"Syncing {unsynced} screenshots..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def update_progress(progress: SyncProgress):
                    if progress.total > 0:
                        progress_bar.progress(progress.processed / progress.total)
                        status_text.text(f"Processing {progress.processed}/{progress.total}...")

                result = sync_screenshots(on_progress=update_progress)
                st.success(f"Synced {result.processed} screenshots!")
                st.rerun()

    with col4:
        safe_mode = st.toggle("Safe Mode", value=True)

    # Safe mode level
    if safe_mode:
        safe_mode_level = st.selectbox(
            "Moderation Level",
            options=["Low", "LowMid", "Mid", "MidHigh", "High", "Very High", "Extreme"],
            index=2
        )
    else:
        safe_mode_level = "Mid"

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
            result_limit = st.slider("Max results", 10, 100, 50, 10)

    # Search button
    if st.button("🔍 Search", type="primary") or (search_term and "last_search" in st.session_state and st.session_state.last_search != search_term):
        if not search_term:
            st.warning("Please enter a search term")
        elif db.get_stats()["synced"] == 0:
            st.warning("No synced screenshots yet. Click 'Sync' first!")
        else:
            st.session_state.last_search = search_term
            remove_temp_images()

            with st.spinner("Searching..."):
                image_paths, similarities = search_images(
                    query=search_term,
                    safe_mode=safe_mode,
                    safe_mode_level=safe_mode_level,
                    negative_texts=negative_texts if not safe_mode else "",
                    negative_weight=negative_weight,
                    limit=result_limit
                )

            if image_paths:
                st.success(f"Found {len(image_paths)} results!")

                # Decrypt images to temp folder
                decrypted_paths = []
                for path in image_paths:
                    temp_path = TEMP_DIR / Path(path).name
                    if encryption_key:
                        EncryptDecryptImage(path, encryption_key, str(temp_path))
                    else:
                        # Just copy if no encryption
                        import shutil
                        shutil.copy(path, temp_path)
                    decrypted_paths.append(str(temp_path))

                # Image slider
                if len(decrypted_paths) > 1:
                    selected_idx = st.slider(
                        "Browse results",
                        0, len(decrypted_paths) - 1, 0
                    )
                else:
                    selected_idx = 0

                # Show selected image
                st.image(decrypted_paths[selected_idx], use_container_width=True)
                st.caption(f"Image {selected_idx + 1} of {len(decrypted_paths)} • Similarity: {similarities[selected_idx]:.2%}")

                # Gallery
                st.subheader("Gallery")
                cols = st.columns(4)
                for i, (path, sim) in enumerate(zip(decrypted_paths, similarities)):
                    with cols[i % 4]:
                        st.image(path, use_container_width=True)
                        st.caption(f"{sim:.1%}")
            else:
                st.warning("No results found. Try a different search term.")

# =============================================================================
# DELETE TAB
# =============================================================================
with tab2:
    st.title("Delete Screenshots")

    stats = db.get_stats()
    st.write(f"Total screenshots: {stats['total_screenshots']}")

    if st.button("🗑️ Clear All Data", type="secondary"):
        if st.checkbox("I understand this will delete ALL screenshots permanently"):
            db.clear_all()
            # Also clear screenshot files
            for f in get_screenshots_dir().iterdir():
                f.unlink()
            st.success("All data cleared!")
            st.rerun()

# =============================================================================
# SETTINGS TAB
# =============================================================================
with tab3:
    st.title("Settings")

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

    selected_mode = st.selectbox(
        "Capture Mode",
        options=list(mode_descriptions.keys()),
        format_func=lambda x: x.title()
    )

    if selected_mode:
        config.capture.set_mode(selected_mode)
        st.info(mode_descriptions[selected_mode])

    st.divider()

    st.subheader("Capture Settings")
    col1, col2 = st.columns(2)

    with col1:
        new_interval = st.number_input(
            "Interval (seconds)",
            min_value=0.5,
            max_value=60.0,
            value=float(config.capture.interval),
            step=0.5
        )
        config.capture.interval = new_interval

    with col2:
        new_threshold = st.slider(
            "Change Threshold",
            min_value=0.5,
            max_value=0.99,
            value=config.capture.threshold,
            step=0.01,
            help="Higher = less sensitive (fewer captures)"
        )
        config.capture.threshold = new_threshold

    st.divider()

    st.subheader("Storage")
    st.code(str(config.data_dir))

    st.subheader("Database")
    st.code(str(config.database_path))
