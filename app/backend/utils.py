import docx
import PyPDF2
from io import BytesIO
from pptx import Presentation


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


def extract_text_from_pptx(content: bytes) -> str:
    prs = Presentation(BytesIO(content))
    text = []

    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, 'text'):
                text.append(shape.text)

    return '\n'.join(text)
