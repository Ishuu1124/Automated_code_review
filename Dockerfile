FROM python:3.11.12-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

ENTRYPOINT ["uvicorn", "app.api.app:app", "--host", "0.0.0.0", "--port", "8080"]