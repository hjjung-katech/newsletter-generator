FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY web/requirements.txt ./web/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install -r web/requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PORT=8000
ENV WEB_CONCURRENCY=2

RUN mkdir -p /app/.local/state/web

EXPOSE 8000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout 300 web.app:app"]
