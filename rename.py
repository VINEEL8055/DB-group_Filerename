import streamlit as st
import pdfplumber
import pytesseract
import re
import io
import pandas as pd


def extract_smo_via_ocr_with_confidence(pdf_file):
    """
    OCR-only extraction for scanned PDFs.
    Returns (SMO_REFERENCE, confidence%)
    """

    best_match = None
    best_confidence = 0

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            image = page.to_image(resolution=300).original

            # OCR with confidence data
            ocr_data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DATAFRAME
            )

            # Drop empty rows
            ocr_data = ocr_data.dropna(subset=["text", "conf"])

            # Normalize text
            ocr_data["clean_text"] = (
                ocr_data["text"].astype(str).str.upper().str.replace(" ", "")
            )

            for _, row in ocr_data.iterrows():
                match = re.search(r"SMO[A-Z0-9]+", row["clean_text"])
                if match:
                    conf = float(row["conf"])
                    if conf > best_confidence:
                        best_match = match.group(0)
                        best_confidence = conf

    if best_match:
        return best_match, round(best_confidence, 2)

    return None, None


# ---------------- STREAMLIT UI ----------------

st.set_page_config(
    page_title="SMO PDF OCR Renamer",
    page_icon="📦",
    layout="centered"
)

st.title("📦 SMO Shipment PDF Renamer (OCR)")
st.write(
    "Upload **scanned shipment PDFs**. "
    "The app uses OCR to detect references starting with **SMO**, "
    "supports **bulk uploads**, and shows **confidence scores**."
)

uploaded_files = st.file_uploader(
    "Upload one or more scanned PDFs",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    st.divider()

    for uploaded_file in uploaded_files:
        st.subheader(f"📄 {uploaded_file.name}")

        with st.spinner("Running OCR..."):
            smo_ref, confidence = extract_smo_via_ocr_with_confidence(uploaded_file)

        if smo_ref:
            st.success(f"✅ Found: **{smo_ref}**")
            st.write(f"📊 OCR Confidence: **{confidence}%**")

            uploaded_file.seek(0)
            pdf_bytes = uploaded_file.read()

            st.download_button(
                label=f"⬇️ Download {smo_ref}.pdf",
                data=pdf_bytes,
                file_name=f"{smo_ref}.pdf",
                mime="application/pdf",
                key=uploaded_file.name
            )
        else:
            st.error("❌ No SMO reference detected")
            st.info(
                "OCR completed but no reference starting with **SMO** was found. "
                "This may be due to a low-quality scan."
            )

        st.divider()
