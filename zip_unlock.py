import streamlit as st
import zipfile
import os
import shutil
from pypdf import PdfReader, PdfWriter
import tempfile

# -----------------------------
# Utility Function
# -----------------------------

def merge_pdfs_from_zip(zip_file):
    # Create unique temp directory for each ZIP
    temp_dir = tempfile.mkdtemp()

    zip_path = os.path.join(temp_dir, zip_file.name)

    # Save uploaded ZIP
    with open(zip_path, "wb") as f:
        f.write(zip_file.getbuffer())

    # Extract ZIP
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    writer = PdfWriter()
    pdf_found = False

    # Walk through extracted folder
    for root, _, files_list in os.walk(temp_dir):
        for file in sorted(files_list):
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    writer.add_page(page)
                pdf_found = True

    if not pdf_found:
        shutil.rmtree(temp_dir)
        raise ValueError(f"No PDFs found in {zip_file.name}")

    output_path = os.path.join(temp_dir, f"{zip_file.name.replace('.zip','')}_merged.pdf")

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path, temp_dir


# -----------------------------
# Streamlit UI
# -----------------------------

st.set_page_config(page_title="Batch ZIP PDF Merger", page_icon="📂")

st.title("📂 Batch ZIP → PDF Merger")
st.write("Upload multiple ZIP files. Each ZIP will generate its own merged PDF.")

uploaded_files = st.file_uploader(
    "Upload one or more ZIP files",
    type=["zip"],
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.divider()
        st.subheader(f"Processing: {uploaded_file.name}")

        try:
            with st.spinner("Merging PDFs..."):
                merged_path, temp_dir = merge_pdfs_from_zip(uploaded_file)

            st.success("✅ Merge completed!")

            with open(merged_path, "rb") as f:
                st.download_button(
                    label=f"⬇ Download {uploaded_file.name.replace('.zip','')}_merged.pdf",
                    data=f,
                    file_name=f"{uploaded_file.name.replace('.zip','')}_merged.pdf",
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"❌ {str(e)}")
