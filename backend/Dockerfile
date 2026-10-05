FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini start.sh ./
COPY alembic ./alembic
COPY app ./app

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# Railway injects PORT; start.sh falls back to 8000 locally.
EXPOSE 8000
CMD ["./start.sh"]
