# Dockerfile
FROM python:3.11-slim

WORKDIR /workspace

# Install uv for rapid package management
RUN pip install --no-cache-dir uv

# Copy requirements from the local build context
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy the rest of the application
COPY . .

EXPOSE 8000
EXPOSE 8501