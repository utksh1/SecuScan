FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY secuscan ./secuscan

EXPOSE 8081

CMD ["uvicorn", "secuscan.main:app", "--host", "0.0.0.0", "--port", "8081"]