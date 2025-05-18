import sys

sys.path.append('../..')

import magic
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

from config import PROJECT_NAME
from utils import extract_text_from_docx, extract_text_from_pdf, extract_text_from_txt, extract_text_from_pptx
from model.model import Model

load_dotenv()

app = FastAPI(title=PROJECT_NAME)
model = Model()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class TextRequest(BaseModel):
    text: str


@app.post('/api/v1/score/text')
async def root(request: TextRequest):
    score = await model.ainvoke({'text': request.text})
    return {'score': score}


@app.post('/api/v1/score/file')
async def analyze_file(file: UploadFile = File(...)):
    content = await file.read()

    # Detect MIME type
    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(content)

    # Extract text based on file type
    try:
        if mime_type == 'text/plain':
            text = extract_text_from_txt(content)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            text = extract_text_from_docx(content)
        elif mime_type == 'application/pdf':
            text = extract_text_from_pdf(content)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
            text = extract_text_from_pptx(content)
        else:
            raise HTTPException(
                status_code=400,
                detail=f'Unsupported file type: {mime_type}. Supported types are: text/plain, application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, application/vnd.openxmlformats-officedocument.presentationml.presentation',
            )

        if not text.strip():
            raise HTTPException(status_code=400, detail='No text content found in the file')

        score = await model.ainvoke({'text': text})

        return {'score': score, 'text': text, 'mime_type': mime_type}
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail='Invalid text encoding. Please ensure the file is UTF-8 encoded.')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error processing file: {str(e)}')
