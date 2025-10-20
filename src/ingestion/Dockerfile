FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-cursor.txt .
RUN pip install --no-cache-dir -r requirements-cursor.txt

# Copy source code
COPY src/ingestion/cursor_client.py /app/src/ingestion/
COPY src/ingestion/ingest_cursor_daily.py /app/src/ingestion/

# Set Python path
ENV PYTHONPATH=/app

# Run ingestion script
CMD ["python3", "/app/src/ingestion/ingest_cursor_daily.py"]
