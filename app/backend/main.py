import sys

sys.path.append('../..')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

from config import PROJECT_NAME
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


@app.post('/api/v1/score')
async def root(request: TextRequest):
    score = await model.ainvoke({'text': request.text})
    return {'score': score}
