FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Build with repo-root context:
#   docker build -f backend/Dockerfile .
# This is required because backend requirements include:
#   -e ../packages/legal-agent-framework
COPY backend/requirements.txt /app/backend/requirements.txt
COPY packages/legal-agent-framework /app/packages/legal-agent-framework
RUN cd /app/backend && pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
