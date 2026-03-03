FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY backend.py .
COPY frontend.html .

# Railway injects PORT automatically
ENV PORT=8000

EXPOSE $PORT

CMD ["python", "backend.py"]
