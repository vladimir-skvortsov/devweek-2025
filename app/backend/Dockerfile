FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONPATH=/app

COPY requirements.txt ../../requirements.txt
RUN pip install --no-cache-dir -r ../../requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
