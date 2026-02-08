import streamlit as st
import pdfplumber
import openai
from io import BytesIO
from docx import Document

# ---------------- CONFIG ----------------
openai.api_key = st.secrets["OPENAI_API_KEY"]

# ---------------- HELPERS ----------------
def extract_pdf_text(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def optimize_resume(resume_text, jd_text):
    prompt = f"""
I am providing two artifacts:

My current resume:
{resume_text}

Target Job Description:
{jd_text}

You are an expert ATS resume optimizer.
Rewrite the resume to be ATS-optimized, entry-level friendly,
STAR-method compliant, truthful, and 1-page.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are an expert ATS resume reviewer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return response.choices[0].message.content


def create_docx(text):
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


# ---------------- UI ----------------
st.set_page_config(page_title="ATS Resume Optimizer", layout="centered")

st.title("📄 ATS Resume Optimizer")
st.caption("Upload your CV, paste a Job Description, get an ATS-ready resume")

cv_file = st.file_uploader("Upload your CV (PDF)", type=["pdf"])
jd_text = st.text_area("Job Description")

if st.button("Optimize Resume"):
    if not cv_file or not jd_text:
        st.error("Please upload CV and paste Job Description")
    else:
        with st.spinner("Extracting resume..."):
            resume_text = extract_pdf_text(cv_file)

        with st.spinner("Optimizing with AI..."):
            optimized_resume = optimize_resume(resume_text, jd_text)

        st.success("Resume optimized!")

        st.subheader("Preview")
        st.text_area(
            "Optimized Resume",
            optimized_resume,
            height=400
        )

        # ---- DOWNLOAD OPTIONS ----
        st.download_button(
            "⬇️ Download as TXT",
            optimized_resume,
            file_name="ATS_Optimized_Resume.txt"
        )

        docx_file = create_docx(optimized_resume)
        st.download_button(
            "⬇️ Download as DOCX",
            docx_file,
            file_name="ATS_Optimized_Resume.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
