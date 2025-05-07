# Dockerfile for Combined Flask App
FROM python:3.9-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application code
COPY . .

EXPOSE 6000

CMD ["python", "app.py"]
