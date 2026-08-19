FROM python:3.12-slim

WORKDIR /app

# Install system dependencies required by RDKit
RUN apt-get update && apt-get install -y \
    curl \
    libxrender1 \
    libxext6 \
    libsm6 \
    libglib2.0-0 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list first for Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Create database directory
RUN mkdir -p /app/database

# Download the ChEMBL SQLite database during IMAGE BUILD
RUN curl -L --fail \
    "https://github.com/Nikkumar-12345/ScaffoldAnalyzer/releases/download/v1.0-db/scaffold_analyzer_chembl.db" \
    -o /app/database/scaffold_analyzer_chembl.db

# Verify that database was downloaded
RUN ls -lh /app/database/scaffold_analyzer_chembl.db

# Render provides PORT dynamically
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]