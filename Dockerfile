FROM python:3.11-slim

WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only first for fast build and small footprint
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend /app/backend
COPY frontend /app/frontend

ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV LLM_PROVIDER=groq
ENV GROQ_MODEL=openai/gpt-oss-20b

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
