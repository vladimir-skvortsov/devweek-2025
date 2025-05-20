FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "dvc[s3]>=3.0.0"

COPY .dvc .dvc
COPY model/ ./model/

RUN dvc config core.no_scm true
RUN dvc pull model/transformer.pth.dvc

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY app/backend/ ./backend/

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
