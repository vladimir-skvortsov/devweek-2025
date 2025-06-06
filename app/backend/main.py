import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import uuid
import os
from typing import Optional

project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

import magic
import torch
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
import structlog

from app.backend.config import PROJECT_NAME
from app.backend.db_client import AirtableClient
from app.backend.utils import (
    extract_text_from_docx,
    extract_text_from_image,
    extract_text_from_pdf,
    extract_text_from_pptx,
    extract_text_from_txt,
)
from model.model import Model

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = structlog.get_logger()

app = FastAPI(
    title=PROJECT_NAME,
    docs_url='/api/docs' if os.getenv('ENVIRONMENT') == 'development' else None,
    redoc_url='/api/redoc' if os.getenv('ENVIRONMENT') == 'development' else None,
)

# CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['POST', 'GET'],
    allow_headers=['*'],
    max_age=3600,
)


# Request tracking middleware
@app.middleware('http')
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    return response


# Security headers middleware
@app.middleware('http')
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response


device = 'cuda' if torch.cuda.is_available() else 'cpu'
model = Model(device=device)
db = AirtableClient()

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # Time window in seconds
MAX_REQUESTS_PER_WINDOW = 10  # Maximum requests allowed per window
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
IP_REQUEST_COUNTS: dict[str, tuple[int, datetime]] = defaultdict(lambda: (0, datetime.now()))


@app.middleware('http')
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    request_id = getattr(request.state, 'request_id', 'unknown')

    # Get current count and timestamp for this IP
    count, timestamp = IP_REQUEST_COUNTS[client_ip]
    current_time = datetime.now()

    # Reset counter if window has passed
    if current_time - timestamp > timedelta(seconds=RATE_LIMIT_WINDOW):
        count = 0
        timestamp = current_time

    # Increment counter
    count += 1
    IP_REQUEST_COUNTS[client_ip] = (count, timestamp)

    # Check if rate limit exceeded
    if count > MAX_REQUESTS_PER_WINDOW:
        logger.warning('rate_limit_exceeded', ip=client_ip, request_id=request_id, count=count)
        return JSONResponse(
            status_code=429,
            content={
                'detail': f'Слишком много запросов. Пожалуйста, попробуйте снова через {RATE_LIMIT_WINDOW} секунд.'
            },
        )

    # Clean up old entries
    if len(IP_REQUEST_COUNTS) > 10000:
        current_time = datetime.now()
        IP_REQUEST_COUNTS.clear()
        logger.info('rate_limit_cache_cleared')

    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error('request_error', ip=client_ip, request_id=request_id, error=str(e))
        raise


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    models: list = Field(
        ...,
    )

    @validator('text')
    def validate_text_length(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Текст не может быть пустым')
        if len(v) > 10000:
            raise ValueError('Длина текста не может превышать 10000 символов')
        return v


class TokenAnalysis(BaseModel):
    token: str
    ai_prob: float  # Higher score means more likely to be AI-written
    is_special_token: bool


class ScoreTextResponse(BaseModel):
    score: float
    tokens: list[TokenAnalysis]
    explanation: str
    examples: str


@app.post('/api/v1/score/text', response_model=ScoreTextResponse)
async def root(request: Request, text_request: TextRequest):
    try:
        logger.info('text_score_request', request_id=request.state.request_id, text_length=len(text_request.text))
        models_list = text_request.models
        models_list += ['transformer']
        result = await model.ainvoke(text_request.text, models_list)

        return {
            'score': result['score'],
            'explanation': result['explanation'],
            'text': text_request.text,
            'tokens': result['tokens'],
            'examples': result['examples'],
        }
    except ValueError as e:
        logger.error('text_score_error', request_id=request.state.request_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error('text_score_unexpected_error', request_id=request.state.request_id, error=str(e))
        raise HTTPException(status_code=500, detail='Ошибка обработки текста')


class ScoreFileResponse(BaseModel):
    score: float
    text: str
    mime_type: str
    tokens: list[TokenAnalysis]
    explanation: str
    examples: str


@app.post('/api/v1/score/file', response_model=ScoreFileResponse)
async def analyze_file(request: Request, file: UploadFile = File(...), models: Optional[str] = None):
    request_id = request.state.request_id
    logger.info('file_score_request', request_id=request_id, filename=file.filename)

    content = await file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        logger.warning('file_too_large', request_id=request_id, size=len(content))
        raise HTTPException(
            status_code=400,
            detail=f'Файл слишком большой. Максимальный размер файла: {MAX_FILE_SIZE // (1024 * 1024)}MB',
        )

    if models is not None and models.strip():
        models_list = [m.strip() for m in models.split(',') if m.strip()]
        if not models_list:
            models_list = ['gpt', 'claude']
        elif not all(m in ['gpt', 'claude'] for m in models_list):
            raise HTTPException(status_code=400, detail='Недопустимые модели. Поддерживаемые модели: gpt, claude')
    else:
        models_list = []
    models_list += ['transformer']

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
                detail=f'Неподдерживаемый тип файла: {mime_type}. Поддерживаемые типы: изображения (PNG, JPEG и т.д.), text/plain, application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, application/vnd.openxmlformats-officedocument.presentationml.presentation',
            )

        if not text.strip():
            raise HTTPException(status_code=400, detail='В файле не найден текстовый контент')

        if len(text) > 10000:
            raise HTTPException(status_code=400, detail='Длина извлеченного текста не может превышать 10000 символов')

        result = await model.ainvoke(text, models_list)

        db.create_record(text, result['tokens'], result['explanation'], result['score'], result['examples'])

        return {
            'score': result['score'],
            'text': text,
            'explanation': result['explanation'],
            'mime_type': mime_type,
            'tokens': result['tokens'],
            'examples': result['examples'],
        }
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail='Некорректная кодировка текста. Пожалуйста, убедитесь, что файл закодирован в UTF-8.',
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Ошибка обработки файла: {str(e)}')


class ShareRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    score: float
    tokens: list[TokenAnalysis]
    explanation: str
    examples: str

    @validator('text')
    def validate_text_length(cls, v):
        if len(v.strip()) == 0:
            raise ValueError('Текст не может быть пустым')
        if len(v) > 10000:
            raise ValueError('Длина текста не может превышать 10000 символов')
        return v


@app.post('/api/v1/text/share')
async def share_text(request: ShareRequest):
    tokens_dict = [token.dict() for token in request.tokens]

    record = db.create_record(
        request.text,
        tokens_dict,
        request.explanation,
        request.score,
        request.examples,
    )

    return {'id': record['id']}


@app.get('/api/v1/text/get')
async def get_shared_text(id: str):
    record = db.get_record_by_id(id)
    if not record:
        raise HTTPException(status_code=404, detail='Запись не найдена')

    return {
        'text': record['text'],
        'score': record['score'],
        'explanation': record['explanation'],
        'tokens': record['tokens'],
        'examples': record['examples'],
    }


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info', proxy_headers=True, forwarded_allow_ips='*')
