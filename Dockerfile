# ===============================
# Base image
# ===============================
FROM python:3.11-slim AS base

WORKDIR /app
COPY apps/api/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ===============================
# Runtime image
# ===============================
FROM base AS runtime
WORKDIR /app
COPY apps/api .

# Set Python path to include the current directory
ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
