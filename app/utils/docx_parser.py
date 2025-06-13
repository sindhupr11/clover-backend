from docx import Document
from io import BytesIO

def extract_text_from_docx(file_bytes):
    doc = Document(BytesIO(file_bytes))
    full_text = "\n".join([para.text for para in doc.paragraphs])
    return full_text
