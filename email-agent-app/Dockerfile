# Dockerfile
FROM python:3.11-slim

WORKDIR /workspace

# Install uv for rapid package management
RUN pip install --no-cache-dir uv

# Copy requirements from the local build context
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Pre-install/cache specific MCP packages (optional but speeds up container boot)
RUN uv pip install --system mcp-server-sqlite

# Copy the rest of the application
COPY . .

CMD ["uvicorn", "main:api", "--host", "0.0.0.0", "--port", "8000"]