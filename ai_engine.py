import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2
import docx
from PIL import Image

# Load Environment Variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file!")

genai.configure(api_key=GEMINI_API_KEY)

def extract_data_from_file(uploaded_file):
    """Extracts text from PDF/DOCX or returns an Image object."""
    if uploaded_file is None:
        return None, None
        
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    try:
        if file_type == "pdf":
            reader = PyPDF2.PdfReader(uploaded_file)
            text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
            return text, None
        elif file_type in ["docx", "doc"]:
            doc = docx.Document(uploaded_file)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text, None
        elif file_type in ["png", "jpg", "jpeg"]:
            image = Image.open(uploaded_file)
            return None, image
    except Exception as e:
        print(f"Error reading file: {e}")
        return None, None
        
    return None, None

def generate_test_questions(domains, num_q, diff_instruction, reference_text=None):
    model = genai.GenerativeModel('gemini-3.6-flash') # Using the model version from your original code
    
    num_domains = len(domains)
    base_q = num_q // num_domains
    remainder = num_q % num_domains
    
    distribution = {}
    for i, d in enumerate(domains):
        distribution[d] = base_q + (1 if i < remainder else 0)
        
    dist_str = ", ".join([f"{count} questions on '{d}'" for d, count in distribution.items() if count > 0])
    
    # 🎯 SMART PROMPT INJECTION: Check if reference material was uploaded
    if reference_text:
        prompt = f"""Generate exactly {num_q} multiple choice questions.
        IMPORTANT: You MUST base your questions STRICTLY on the following reference material provided below. Do not use outside knowledge if it contradicts the reference document.
        
        --- REFERENCE MATERIAL START ---
        {reference_text}
        --- REFERENCE MATERIAL END ---
        
        You MUST divide the questions exactly as follows: {dist_str}.
        The questions MUST be ordered section-wise.
        Difficulty Level: {diff_instruction}.
        Return ONLY a valid JSON array. Each object MUST have exact keys: 'domain', 'question', 'options' (a list of 4 strings), 'answer', and 'explanation'. Do not include any formatting markdown or extra text."""
    else:
        # Standard Prompt for normal generation without files
        prompt = f"""Generate exactly {num_q} multiple choice questions.
        You MUST divide the questions exactly as follows: {dist_str}.
        The questions MUST be ordered section-wise.
        Difficulty Level: {diff_instruction}.
        Return ONLY a valid JSON array. Each object MUST have exact keys: 'domain', 'question', 'options' (a list of 4 strings), 'answer', and 'explanation'. Do not include any formatting markdown or extra text."""
    
    response = model.generate_content(prompt)
    text = response.text
    
    # Advanced Safe JSON Parsing
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
        
    return json.loads(text.strip())