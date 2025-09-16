# frontend/streamlit_app.py
import os
import requests
import streamlit as st

# Backend URL
DEFAULT_BACKEND = "http://localhost:10000/api"
BACKEND_URL = os.getenv("BACKEND_URL", DEFAULT_BACKEND).rstrip("/")

st.set_page_config(page_title="Zoomage NASA Explorer", page_icon="🚀", layout="wide")
st.title("🚀 Zoomage — NASA Image Explorer")

st.write("Search NASA images, view them, and request AI analysis.")

query = st.text_input("Search (e.g. Mars, Apollo, Earth, Nebula)")
col1, col2 = st.columns([3,1])
with col2:
    media = st.selectbox("Media type", ["image"], index=0)

if st.button("Search"):
    if not query.strip():
        st.warning("Enter a search term first.")
    else:
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
                if st.button(f"Analyze {img.get('nasa_id')}", key=f"analyze_{img.get('nasa_id')}"):
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
