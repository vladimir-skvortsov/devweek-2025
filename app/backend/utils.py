import docx
import PyPDF2
from io import BytesIO


def extract_text_from_txt(content: bytes) -> str:
    return content.decode('utf-8')


def extract_text_from_docx(content: bytes) -> str:
    doc = docx.Document(BytesIO(content))
    return '\n'.join([paragraph.text for paragraph in doc.paragraphs])


def extract_text_from_pdf(content: bytes) -> str:
    pdf_file = BytesIO(content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ''
    for page in pdf_reader.pages:
        text += page.extract_text() + '\n'
    return text
