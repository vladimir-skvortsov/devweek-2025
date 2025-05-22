FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install "dvc[s3]>=3.0.0"

COPY . .

RUN dvc config core.no_scm true
RUN dvc pull model/transformer.pth.dvc

WORKDIR /

ENV PYTHONPATH=/

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt


EXPOSE 8000

CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
