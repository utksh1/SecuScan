FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY secuscan ./secuscan
COPY plugins ./plugins

EXPOSE 8081

CMD ["uvicorn", "secuscan.api:app", "--host", "127.0.0.1", "--port", "8081"]

