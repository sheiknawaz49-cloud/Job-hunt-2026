# tools/resume_extractor.py
from pathlib import Path
from pypdf import PdfReader


def extract_resume_text(pdf_path: str = "resume.pdf") -> str:
    """Extracts raw text from the candidate's PDF resume."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Resume file not found at {pdf_path}")

    reader = PdfReader(str(path))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)

    full_text = "\n".join(pages_text).strip()
    if not full_text:
        raise ValueError("Could not extract any readable text from the resume PDF.")
    
    return full_text