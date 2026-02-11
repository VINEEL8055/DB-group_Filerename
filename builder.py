import streamlit as st
import openai
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import re

# Try importing PDF reader - handle both package names
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

# Import for PDF generation
from fpdf import FPDF

# Page configuration
st.set_page_config(
    page_title="ATS Resume Optimizer",
    page_icon="📄",
    layout="centered"
)

# Title
st.title("📄 ATS Resume Optimizer")
st.markdown("Upload your CV and optimize it for Applicant Tracking Systems")

# API Key in sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    openai_api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="Enter your OpenAI API key to use the optimizer"
    )
    
    st.markdown("---")
    st.markdown("### Email Settings (Optional)")
    st.markdown("*Fill these to receive results via email*")
    
    smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
    smtp_port = st.number_input("SMTP Port", value=587, min_value=1, max_value=65535)
    sender_email = st.text_input("Sender Email")
    sender_password = st.text_input("Sender Password", type="password")

# System prompt for AI
SYSTEM_PROMPT = """ROLE

You are an expert ATS resume optimizer, professional resume writer, and recruiter-level resume reviewer with experience evaluating entry-level and new graduate candidates.

Your task is to revise my resume so it is ATS-optimized and tightly aligned to the target job description (JD), while remaining truthful, defensible, and interview-ready.

SOURCE & INTEGRITY RULES (MANDATORY)

Treat the resume I provide as the single source of truth.

Do NOT invent experience, skills, tools, certifications, or metrics.

Only rephrase, reorder, condense, or strengthen content that is clearly supported by the resume.

If a skill or tool is not explicitly or implicitly supported, do not include it.

If a metric is missing, use conservative, realistic estimates or clear qualitative outcomes (e.g., "improved reliability," "reduced manual effort").

TARGET PROFILE

Target Seniority:

Optimize this resume for a New Grad / Entry-Level role.

Use appropriate scope, ownership, and language for early-career candidates.

Emphasize hands-on execution, learning velocity, and measurable contributions over senior leadership claims.

KEYWORD & ATS OPTIMIZATION

Analyze the job description to identify:

Required and preferred hard skills

Tools, technologies, and platforms

Domain-specific keywords

Integrate keywords naturally across:

Summary

Experience bullet points

Skills section

Do NOT keyword-stuff or repeat keywords unnaturally.

Favor exact keyword matches when appropriate (e.g., "SQL," "Power BI," "ETL").

STAR METHOD (STRICT ENFORCEMENT)

EVERY experience bullet point MUST follow the STAR method:

Action Verb: Start with a strong verb

Task/Problem: What was being solved

Action: What was done and how

Result: Measurable outcome or clear business impact

● If a bullet does NOT clearly end with a result, rewrite it until it does.

Each bullet must be 1—2 lines max

Avoid responsibility-only bullets

Avoid vague phrasing such as:

"worked on"

"helped with"

"responsible for"

"involved in"

ROLE ALIGNMENT & STRUCTURE

Identify experiences most relevant to the JD and place them first.

Reorder bullets within each role so the strongest, most relevant impact appears at the top.

Condense or remove content that does not strengthen candidacy for this role.

ATS-FRIENDLY FORMATTING (STRICT)

Use ONLY these section headers:

Summary

Impact Snapshot

Experience

Education

Skills

Use plain text formatting

Use bullet points with *

Do NOT use:

Tables

Columns

Icons

Graphics

Text boxes

Ensure the resume is fully parsable by ATS systems.

PROFESSIONAL VOICE & CLARITY

Use confident, concise, professional language

Avoid first-person language ("I", "my")

Focus on outcomes, efficiency gains, accuracy, scale, or user impact

Ensure the resume reads naturally for human recruiters, not just ATS

IMPACT SNAPSHOT (REQUIRED)

Place immediately after the Summary

Include 3—5 bullets only

Each bullet must:

Be one line

Highlight a high-impact, quantified outcome

Focus on business value, efficiency, scale, or decision-making impact

Avoid repeating the same metric used multiple times

LENGTH & BALANCE

Keep the resume to 1 page for entry-level candidates

Avoid over-detailing academic projects unless directly relevant

Prioritize clarity over density

FINAL OUTPUT REQUIREMENTS

Deliver a complete, revised resume in plain text

Include:

A JD-aligned Summary

An Impact Snapshot directly after the Summary

A Skills section aligned to the JD

Verify before finalizing that:

Every experience bullet is STAR-compliant

Every claim is truthful and defensible

Formatting is ATS-safe

If any bullet does not meet these standards, rewrite it before outputting the final resume"""


def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file"""
    try:
        pdf_reader = PdfReader(io.BytesIO(pdf_file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None


def optimize_resume(cv_text, job_description, api_key):
    """Call OpenAI API to optimize resume"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        user_prompt = f"""I am providing two artifacts:

My current resume:
{cv_text}

A target job description (JD) for the role I am applying to:
{job_description}"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )
        
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error calling OpenAI API: {str(e)}")
        return None


class PDF(FPDF):
    """Custom PDF class for resume"""
    def header(self):
        pass
    
    def footer(self):
        pass


def create_pdf(text):
    """Convert resume text to PDF format using FPDF"""
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        if not line:
            pdf.ln(3)
            continue
        
        # Clean special characters that might cause issues
        clean_line = line
        # Replace common problematic characters
        clean_line = clean_line.replace('—', '-')  # em dash
        clean_line = clean_line.replace('–', '-')  # en dash
        clean_line = clean_line.replace('"', '"')  # smart quotes
        clean_line = clean_line.replace('"', '"')
        clean_line = clean_line.replace(''', "'")
        clean_line = clean_line.replace(''', "'")
        clean_line = clean_line.replace('…', '...')
        # Remove markdown bold markers for display
        clean_line = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_line)
        
        # Encode to handle any remaining special characters
        try:
            # Remove any non-ASCII characters
            clean_line = ''.join(char if ord(char) < 128 else ' ' for char in clean_line)
        except:
            clean_line = ''.join(char for char in clean_line if ord(char) < 128)
        
        # Handle different types of content
        try:
            if line.startswith('# '):
                # Main title
                pdf.set_font('Arial', 'B', 16)
                text_content = clean_line.replace('# ', '')
                if text_content:
                    pdf.multi_cell(0, 8, text_content)
                pdf.ln(2)
            elif line.startswith('## '):
                # Section heading
                pdf.set_font('Arial', 'B', 12)
                pdf.ln(2)
                text_content = clean_line.replace('## ', '')
                if text_content:
                    pdf.multi_cell(0, 6, text_content)
                pdf.ln(1)
            elif line.startswith('### '):
                # Subsection
                pdf.set_font('Arial', 'B', 10)
                text_content = clean_line.replace('### ', '')
                if text_content:
                    pdf.multi_cell(0, 5, text_content)
                pdf.ln(1)
            elif line.startswith('* '):
                # Bullet point
                pdf.set_font('Arial', '', 9)
                text_content = clean_line.replace('* ', '- ')
                if text_content:
                    pdf.multi_cell(0, 5, text_content)
            elif line == '---':
                # Horizontal rule
                pdf.ln(2)
            else:
                # Normal text
                pdf.set_font('Arial', '', 10)
                if clean_line:
                    pdf.multi_cell(0, 5, clean_line)
        except Exception as e:
            # If any line fails, skip it and continue
            print(f"Skipping line due to error: {str(e)}")
            continue
    
    # Return PDF as bytes using fpdf2 syntax
    return pdf.output()


def send_email(recipient_email, pdf_data, smtp_server, smtp_port, sender_email, sender_password):
    """Send email with optimized resume as PDF attachment"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = "Your ATS Optimized Resume"
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        # Email body
        body = """Hello,

Your ATS-optimized resume is attached to this email.

Best regards,
ATS Resume Optimizer"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF
        pdf_attachment = MIMEBase('application', 'pdf')
        pdf_attachment.set_payload(pdf_data)
        encoders.encode_base64(pdf_attachment)
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='optimized_resume.pdf')
        msg.attach(pdf_attachment)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False


# Main form
with st.form("resume_form"):
    st.subheader("📤 Upload Your Information")
    
    cv_file = st.file_uploader(
        "Upload CV (PDF)",
        type=['pdf'],
        help="Upload your current resume in PDF format"
    )
    
    job_description = st.text_area(
        "Job Description",
        height=200,
        help="Paste the job description you're applying for"
    )
    
    email_id = st.text_input(
        "Email ID (Optional)",
        help="Enter your email to receive the optimized resume"
    )
    
    submit_button = st.form_submit_button("🚀 Optimize Resume")

# Process form submission
if submit_button:
    # Validation
    if not openai_api_key:
        st.error("⚠️ Please enter your OpenAI API key in the sidebar")
    elif not cv_file:
        st.error("⚠️ Please upload your CV")
    elif not job_description:
        st.error("⚠️ Please enter the job description")
    else:
        with st.spinner("🔄 Extracting text from CV..."):
            cv_text = extract_text_from_pdf(cv_file)
        
        if cv_text:
            with st.spinner("🤖 Optimizing your resume with AI... This may take a minute."):
                optimized_resume = optimize_resume(cv_text, job_description, openai_api_key)
            
            if optimized_resume:
                st.success("✅ Resume optimized successfully!")
                
                # Display the result
                st.subheader("📋 Your Optimized Resume")
                st.markdown(optimized_resume)
                
                # Generate PDF
                with st.spinner("📄 Generating PDF..."):
                    pdf_data = create_pdf(optimized_resume)
                
                # Download button for PDF
                st.download_button(
                    label="📥 Download Optimized Resume (PDF)",
                    data=pdf_data,
                    file_name="optimized_resume.pdf",
                    mime="application/pdf"
                )
                
                # Also offer text download
                st.download_button(
                    label="📝 Download as Text",
                    data=optimized_resume,
                    file_name="optimized_resume.txt",
                    mime="text/plain"
                )
                
                # Send email if requested and configured
                if email_id and sender_email and sender_password:
                    with st.spinner("📧 Sending email..."):
                        if send_email(email_id, pdf_data, smtp_server, smtp_port, sender_email, sender_password):
                            st.success(f"✅ Email with PDF sent to {email_id}")
                        else:
                            st.warning("⚠️ Resume optimized but email failed to send")
                elif email_id:
                    st.info("ℹ️ To send emails, configure SMTP settings in the sidebar")

# Footer
st.markdown("---")
st.markdown("""
### 📚 How to Use
1. Enter your **OpenAI API Key** in the sidebar
2. Upload your current **CV in PDF format**
3. Paste the **Job Description** you're targeting
4. (Optional) Configure email settings to receive results via email
5. Click **Optimize Resume** to get your ATS-optimized version

**Note:** The optimizer uses GPT-4o-mini to analyze and improve your resume based on the job description.
""")
