import sys

sys.path.append('../..')

import magic
import torch
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

from config import PROJECT_NAME
from utils import (
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
    extract_text_from_pptx,
    extract_text_from_image,
)
from model.model import Model

load_dotenv()

app = FastAPI(title=PROJECT_NAME)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = Model(device=device)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)

    @validator('text')
    def validate_text_length(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Text cannot be empty')
        if len(v) > 10000:
            raise ValueError('Text length cannot exceed 10000 characters')
        return v


@app.post('/api/v1/score/text')
async def root(request: TextRequest):
    try:
        score = await model.ainvoke({'text': request.text})
        return {'score': score}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post('/api/v1/score/file')
async def analyze_file(file: UploadFile = File(...)):
    content = await file.read()

    # Detect MIME type
    mime = magic.Magic(mime=True)
    mime_type = mime.from_buffer(content)

    # Extract text based on file type
    try:
        if mime_type.startswith('image/'):
            text = extract_text_from_image(content)
        elif mime_type == 'text/plain':
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
                detail=f'Unsupported file type: {mime_type}. Supported types are: images (PNG, JPEG, etc.), text/plain, application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, application/vnd.openxmlformats-officedocument.presentationml.presentation',
            )

        if not text.strip():
            raise HTTPException(status_code=400, detail='No text content found in the file')

        if len(text) > 10000:
            raise HTTPException(status_code=400, detail='Extracted text length cannot exceed 10000 characters')

        score = await model.ainvoke({'text': text})

        return {'score': score, 'text': text, 'mime_type': mime_type}
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail='Invalid text encoding. Please ensure the file is UTF-8 encoded.')
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error processing file: {str(e)}')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)
