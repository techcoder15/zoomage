# frontend/streamlit_app.py
import os
import requests
import streamlit as st

# Use this when testing locally
DEFAULT_BACKEND = "http://localhost:10000/api"
BACKEND_URL = os.getenv("BACKEND_URL", DEFAULT_BACKEND).rstrip("/")

st.set_page_config(page_title="Zoomage NASA Explorer", page_icon="🚀", layout="wide")
st.title("🚀 Zoomage — NASA Image Explorer")

st.write("Search NASA images, view them, and request AI analysis.")

# --- Search UI ---
query = st.text_input("Search (e.g. Mars, Apollo, Earth, Nebula)")
col1, col2 = st.columns([3,1])
with col2:
    media = st.selectbox("Media type", ["image"], index=0)

if st.button("Search"):
    if not query.strip():
        st.warning("Enter a search term first.")
    else:
        with st.spinner("Searching NASA..."):
            try:
                resp = requests.post(f"{BACKEND_URL}/search", json={"query": query, "media_type": media}, timeout=30)
                resp.raise_for_status()
                images = resp.json()
            except Exception as e:
                st.error(f"Search failed: {e}")
                images = []

        if images:
            st.write(f"Found {len(images)} images")
            for img in images:
                st.image(img.get("url"), caption=img.get("title") or img.get("nasa_id"), use_column_width=True)
                with st.expander("Details"):
                    st.write(img.get("description") or "No description.")
                    st.write("Keywords:", img.get("keywords", []))
                    # Analyze button per image
                    if st.button(f"Analyze {img.get('nasa_id')}", key=f"analyze_{img.get('nasa_id')}"):
                        with st.spinner("Running AI analysis..."):
                            try:
                                aresp = requests.post(
                                    f"{BACKEND_URL}/analyze",
                                    json={"image_url": img.get("url"), "analysis_type": "general"},
                                    timeout=60
                                )
                                aresp.raise_for_status()
                                analysis = aresp.json().get("analysis", "")
                                st.subheader("AI analysis")
                                st.write(analysis)
                            except Exception as ex:
                                st.error(f"AI analysis failed: {ex}")
        else:
            st.info("No results returned.")

# --- Saved images (optional) ---
if st.button("Show saved images"):
    with st.spinner("Loading saved images..."):
        try:
            r = requests.get(f"{BACKEND_URL}/images", timeout=20)
            r.raise_for_status()
            saved = r.json()
        except Exception as e:
            st.error(f"Could not load saved images: {e}")
            saved = []
    if saved:
        st.write(f"Saved images: {len(saved)}")
        for s in saved:
            st.image(s.get("url"), caption=s.get("title"), use_column_width=True)
    else:
        st.write("No saved images found.")
