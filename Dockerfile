FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/data/schedule.db \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY static/ ./static/

# Schedule data lives here — mount a named volume or host dir to persist it.
VOLUME ["/data"]

EXPOSE 8000

# Single worker + threads: SQLite is happiest without concurrent writers, and
# the load here is trivial.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "8", "server:app"]
