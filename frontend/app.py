import streamlit as st
import requests

API_URL = "https://zoomage-1234.streamlit.app/api"

st.title("🚀 Zoomage NASA Explorer")

query = st.text_input("Search NASA images")
if st.button("Search"):
    resp = requests.post(f"{API_URL}/search", json={"query": query})
    if resp.status_code == 200:
        images = resp.json()
        for img in images:
            st.image(img["url"], caption=img["title"])
            if st.button(f"Analyze {img['nasa_id']}"):
                analysis = requests.post(f"{API_URL}/analyze", json={"image_url": img["url"]})
                st.write(analysis.json()["analysis"])
    else:
        st.error(resp.text)
