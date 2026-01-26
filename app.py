import streamlit as st
import os
import re
import csv
import shutil
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Shipment OCR Renamer", layout="wide")

ID_REGEX = re.compile(r"\bS[A-Z0-9]{6,}\b")
KEYWORDS_SHIPMENT = ("SHIPMENT NUMBER", "SHIPMENT#", "SHIPMENT NO", "SHIPMENT")
KEYWORDS_REFERENCE = ("REFERENCES", "REFERENCE", "REF")

BASE_DIR = Path("runtime")
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
TMP_DIR = BASE_DIR / "tmp"

for d in [INPUT_DIR, OUTPUT_DIR, TMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ---------------- HELPERS ----------------
def normalize_text(s):
    return s.replace("\u00A0", " ").replace("\t", " ")


def score_candidate(line, token):
    score = 0
    if any(k in line for k in KEYWORDS_SHIPMENT):
        score += 100
    if any(k in line for k in KEYWORDS_REFERENCE):
        score += 60
    score += len(token)
    return score


def extract_best_id(text):
    lines = normalize_text(text).splitlines()
    candidates = []

    for line in lines:
        up = line.upper()
        for m in ID_REGEX.findall(up):
            candidates.append({
                "token": m,
                "line": up,
                "score": score_candidate(up, m)
            })

    if not candidates:
        return None, "UNMATCHED"

    ship = [c for c in candidates if any(k in c["line"] for k in KEYWORDS_SHIPMENT)]
    if ship:
        return max(ship, key=lambda x: x["score"])["token"], "SHIPMENT"

    ref = [c for c in candidates if any(k in c["line"] for k in KEYWORDS_REFERENCE)]
    if ref:
        return max(ref, key=lambda x: x["score"])["token"], "REFERENCE"

    return max(candidates, key=lambda x: x["score"])["token"], "FALLBACK"


def run_ocr(input_pdf, out_pdf, txt_file):
    cmd = [
        "ocrmypdf",
        "--force-ocr",
        "--sidecar", str(txt_file),
        str(input_pdf),
        str(out_pdf)
    ]
    subprocess.run(cmd, check=True)


# ---------------- UI ----------------
st.title("📄 Shipment OCR & Auto-Renamer")
st.markdown("Upload scanned PDFs → OCR → Extract **Shipment/Reference IDs starting with `S`** → Rename automatically")

uploaded_files = st.file_uploader(
    "Upload scanned PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} files uploaded")

    if st.button("🚀 Run OCR & Rename"):
        progress = st.progress(0)
        log_rows = []

        for i, file in enumerate(uploaded_files):
            try:
                input_path = INPUT_DIR / file.name
                with open(input_path, "wb") as f:
                    f.write(file.getbuffer())

                ocr_pdf = TMP_DIR / f"{input_path.stem}_ocr.pdf"
                txt_file = TMP_DIR / f"{input_path.stem}.txt"

                run_ocr(input_path, ocr_pdf, txt_file)

                text = txt_file.read_text(errors="ignore")
                extracted_id, rule = extract_best_id(text)

                if extracted_id:
                    out_name = f"{extracted_id}.pdf"
                    status = "OK"
                else:
                    out_name = f"UNMATCHED_{file.name}"
                    status = "UNMATCHED"

                shutil.copy2(ocr_pdf, OUTPUT_DIR / out_name)

                log_rows.append([
                    datetime.now().isoformat(),
                    file.name,
                    extracted_id or "",
                    rule,
                    out_name,
                    status
                ])

            except Exception as e:
                shutil.copy2(input_path, OUTPUT_DIR / f"ERROR_{file.name}")
                log_rows.append([
                    datetime.now().isoformat(),
                    file.name,
                    "",
                    "ERROR",
                    f"ERROR_{file.name}",
                    str(e)
                ])

            progress.progress((i + 1) / len(uploaded_files))

        # Write CSV log
        log_path = OUTPUT_DIR / "rename_log.csv"
        with open(log_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "original_file", "extracted_id", "rule", "output_file", "status"])
            writer.writerows(log_rows)

        # Zip output
        zip_path = BASE_DIR / "renamed_pdfs.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in OUTPUT_DIR.iterdir():
                zipf.write(file, file.name)

        st.success("✅ Processing complete")

        st.dataframe(
            {
                "Original": [r[1] for r in log_rows],
                "Extracted ID": [r[2] for r in log_rows],
                "Rule Used": [r[3] for r in log_rows],
                "Status": [r[5] for r in log_rows],
            }
        )

        with open(zip_path, "rb") as f:
            st.download_button(
                "⬇️ Download Renamed PDFs (ZIP)",
                f,
                file_name="renamed_pdfs.zip",
                mime="application/zip"
            )
