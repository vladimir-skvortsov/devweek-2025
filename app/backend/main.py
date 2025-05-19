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
from model.utils.OpenRouter import OpenRouter
import json
load_dotenv()

app = FastAPI(title=PROJECT_NAME)
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = Model(device=device)
chat = OpenRouter(model_name='openai/o4-mini', temperature=0.7)
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
        # 2) Формируем prompt, теперь с самим текстом
        prompt = (
            f"You are an expert interpreter of AI Text Detector outputs. "
            f"The detector has assigned the following input text a human-likeness score of {score * 100:.1f}%.\n\n"
            "=== Begin Input Text ===\n"
            f"{request.text}\n"
            "=== End Input Text ===\n\n"
            "Please provide a single, comprehensive explanation—of at least 150 words—"
            "describing exactly why the model evaluated this text this way. "
            "In your analysis, focus on the internal criteria of the neural detector, such as:\n"
            "- Vocabulary richness (diversity of words, rare or idiomatic expressions)\n"
            "- Syntactic complexity (sentence length variation, subordinate clauses, punctuation patterns)\n"
            "- Semantic coherence (logical flow, thematic consistency)\n"
            "- Stylistic markers (tone, personalization, emotional nuance, use of anecdotes)\n"
            "- Repetitive or templated phrasing indicative of algorithmic output\n\n"
            "Return strictly a JSON object in this exact format:\n"
            "{\n"
            "  \"explanation\": \"<your detailed analysis here>\"\n"
            "}\n"
            "Do not include any additional keys, comments or free-form text outside of this JSON."
        )

        resp_msg = await chat.ainvoke(prompt)
        resp_text = getattr(resp_msg, 'content', str(resp_msg))

        try:
            payload = json.loads(resp_text)
            explanation = payload.get('explanation', '')
        except json.JSONDecodeError:
            explanation = resp_text

        return {
            'score': score,
            'explanation': explanation
        }
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
