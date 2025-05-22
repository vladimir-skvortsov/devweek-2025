FROM python:3.11-slim

WORKDIR /app

COPY ./app/tg_bot/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-u", "app/tg_bot/bot.py"]
