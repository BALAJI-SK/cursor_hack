FROM python:3.11-slim

# Install unrar binary dependencies for CBR/RAR extraction
RUN apt-get update && apt-get install -y --no-install-recommends \
    unrar-free \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure uploads/ directory is created for database and file storage
RUN mkdir -p uploads

COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
