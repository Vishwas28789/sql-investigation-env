FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install fastapi uvicorn pydantic python-multipart openai

COPY . .

RUN pip install -e . --no-deps 2>/dev/null || true

ENV PYTHONPATH=/app

EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
