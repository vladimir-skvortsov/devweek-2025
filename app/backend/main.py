import sys

sys.path.append('../..')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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


@app.get('/api/v1/score')
async def root(text: str):
    score = await model.ainvoke({'text': text})
    return {'score': score}
