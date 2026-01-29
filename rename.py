import streamlit as st
import pdfplumber
import pytesseract
import re
import io


def extract_smo_via_ocr(pdf_file):
    """
    OCR-based extraction for scanned PDFs.
    Looks for any reference starting with 'SMO'
    """
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            # Convert page to image
            image = page.to_image(resolution=300).original

            # OCR the image
            text = pytesseract.image_to_string(image)

            # Normalize OCR output (remove spaces/newlines)
            cleaned_text = re.sub(r"\s+", "", text.upper())

            match = re.search(r"SMO[A-Z0-9]+", cleaned_text)
            if match:
                return match.group(0)

    return None


st.set_page_config(
    page_title="SMO PDF OCR Renamer",
    page_icon="📦",
    layout="centered"
)

st.title("📦 SMO Shipment PDF Renamer (OCR)")
st.write(
    "Designed for **scanned shipment PDFs**. "
    "The app uses OCR to detect any reference starting with **SMO**."
)

uploaded_file = st.file_uploader(
    "Upload scanned shipment PDF",
    type=["pdf"]
)

if uploaded_file:
    with st.spinner("Running OCR and detecting SMO reference..."):
        smo_ref = extract_smo_via_ocr(uploaded_file)

    if smo_ref:
        st.success(f"✅ SMO Reference Found: **{smo_ref}**")

        uploaded_file.seek(0)
        pdf_bytes = uploaded_file.read()

        st.download_button(
            label="⬇️ Download Renamed PDF",
            data=pdf_bytes,
            file_name=f"{smo_ref}.pdf",
            mime="application/pdf"
        )
    else:
        st.error("❌ No SMO reference detected")
        st.info(
            "OCR ran successfully, but no reference starting with **SMO** "
            "was found. Try a clearer scan if possible."
        )
