import docx
import PyPDF2
from io import BytesIO
from pptx import Presentation
import pytesseract
from PIL import Image


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


def extract_text_from_image(content: bytes) -> str:
    try:
        # Open the image using PIL
        image = Image.open(BytesIO(content))

        # Convert to RGB if necessary (for PNG with transparency)
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # Extract text using Tesseract OCR
        text = pytesseract.image_to_string(image, lang='rus+eng')

        return text.strip()
    except Exception as e:
        raise ValueError(f'Failed to process image: {str(e)}')
