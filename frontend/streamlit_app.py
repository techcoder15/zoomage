import streamlit as st
from backend.server import process_image   # ✅ import from backend


st.set_page_config(page_title="Zoomage", layout="wide")

st.title("🔍 Zoomage - Image Processing App")
st.write("Upload an image and see the processing result instantly!")

# File uploader
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)

    # Process button
    if st.button("Process Image"):
        with st.spinner("Processing..."):
            result = process_image(uploaded_file)  # call your backend function
        st.success("Processing complete!")
        st.image(result, caption="Processed Image", use_column_width=True)

st.markdown("---")
st.caption("Built with ❤️ using Streamlit")
