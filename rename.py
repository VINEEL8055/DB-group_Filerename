import streamlit as st
import pdfplumber
import re
import io


def extract_smo_reference(pdf_file):
    """
    Extracts the first reference starting with 'SMO' from the PDF
    """
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            match = re.search(r"\bSMO[A-Z0-9]+\b", text)
            if match:
                return match.group(0)

    return None


st.set_page_config(
    page_title="SMO Shipment PDF Renamer",
    page_icon="📦",
    layout="centered"
)

st.title("📦 SMO Shipment PDF Renamer")
st.write(
    "Upload a shipment PDF. The app will automatically detect the **SMO reference** "
    "and rename the file for download."
)

uploaded_file = st.file_uploader(
    "Upload PDF file",
    type=["pdf"]
)

if uploaded_file:
    with st.spinner("Scanning PDF for SMO reference..."):
        smo_ref = extract_smo_reference(uploaded_file)

    if smo_ref:
        st.success(f"✅ SMO Reference Found: **{smo_ref}**")

        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()

        renamed_file = io.BytesIO(pdf_bytes)

        st.download_button(
            label="⬇️ Download Renamed PDF",
            data=renamed_file,
            file_name=f"{smo_ref}.pdf",
            mime="application/pdf"
        )
    else:
        st.error("❌ No SMO reference found in this PDF.")
        st.info("Make sure the PDF contains a reference starting with **SMO**.")
