FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r backend/requirements.txt

ENV PYTHONPATH=/app/backend

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]