import streamlit as st
import zipfile
import os
import shutil
from pypdf import PdfReader, PdfWriter
import tempfile

# -----------------------------
# Utility Functions
# -----------------------------

def reset_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    os.makedirs(folder_path)

def merge_pdfs_from_zip(zip_file, output_path):
    extract_dir = "extracted_pdfs"

    # Reset folder every run
    reset_folder(extract_dir)

    # Save uploaded ZIP temporarily
    temp_zip_path = os.path.join(extract_dir, "uploaded.zip")
    with open(temp_zip_path, "wb") as f:
        f.write(zip_file.getbuffer())

    # Extract ZIP
    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    writer = PdfWriter()
    pdf_found = False

    for root, _, files_list in os.walk(extract_dir):
        for file in sorted(files_list):
            if file.lower().endswith(".pdf"):
                pdf_path = os.path.join(root, file)
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    writer.add_page(page)
                pdf_found = True

    if not pdf_found:
        raise ValueError("No PDF files found in the ZIP.")

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path

# -----------------------------
# Streamlit UI
# -----------------------------

st.set_page_config(page_title="ZIP PDF Merger", page_icon="📄")

st.title("📄 ZIP to Merged PDF Tool")
st.write("Upload a ZIP file containing PDFs and merge them automatically.")

uploaded_file = st.file_uploader("Upload ZIP file", type=["zip"])

if uploaded_file is not None:
    try:
        with st.spinner("Merging PDFs..."):
            output_file = "merged_output.pdf"
            merged_path = merge_pdfs_from_zip(uploaded_file, output_file)

        st.success("✅ PDF merged successfully!")

        with open(merged_path, "rb") as f:
            st.download_button(
                label="⬇ Download Merged PDF",
                data=f,
                file_name="merged_output.pdf",
                mime="application/pdf"
            )

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
