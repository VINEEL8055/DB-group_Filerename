import streamlit as st
import pdfplumber
import pytesseract
import re
import numpy as np
from PIL import Image, ImageEnhance
import io


# ---------------- IMAGE PREPROCESSING ---------------- #

def preprocess_image(img):
    """
    Improve scanned image quality for OCR
    """
    img = img.convert("L")  # grayscale
    img = ImageEnhance.Contrast(img).enhance(2.0)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    return img


# ---------------- OCR + CONFIDENCE ---------------- #

def extract_smo_via_ocr_with_confidence(pdf_file):
    best_match = None
    best_confidence = 0

    custom_config = (
        "--oem 3 "
        "--psm 6 "
        "-c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    )

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            img = page.to_image(resolution=300).original
            img = preprocess_image(img)

            data = pytesseract.image_to_data(
                img,
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )

            tokens = []
            confidences = []

            for text, conf in zip(data["text"], data["conf"]):
                if conf != "-1" and text.strip():
                    tokens.append(text.upper())
                    confidences.append(float(conf))

            combined_text = "".join(tokens)

            match = re.search(r"SMO[A-Z0-9]{6,}", combined_text)
            if match and confidences:
                avg_conf = round(np.mean(confidences), 2)

                if avg_conf > best_confidence:
                    best_match = match.group(0)
                    best_confidence = avg_conf

    if best_match:
        return best_match, best_confidence

    return None, None


# ---------------- STREAMLIT UI ---------------- #

st.set_page_config(
    page_title="SMO Shipment PDF Renamer (OCR)",
    page_icon="📦",
    layout="centered"
)

st.title("📦 SMO Shipment PDF Renamer (OCR)")
st.write(
    "Upload **scanned shipment PDFs**. "
    "The app extracts **SMO reference numbers**, boosts OCR confidence, "
    "and lets you download renamed files."
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
            st.success(f"✅ SMO Reference Found: **{smo_ref}**")
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
                "OCR completed, but no valid reference starting with **SMO** "
                "was found. This may be due to a low-quality scan."
            )

        st.divider()
