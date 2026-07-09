# Use a lightweight Python image
FROM python:3.11-slim

WORKDIR /workspace

# Copy dependencies and install
COPY ../requirements.txt .
RUN pip install uv
RUN uv init && uv sync && uv add -r requirements.txt

# Copy source code
COPY . .
# Copy environment variables file
COPY ../.env .env

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000
EXPOSE 8501

# Start both services (for simple local setups, a bash script or supervisor works)
CMD ["sh", "-c", "uvicorn app.main:api --host 0.0.0.0 --port 8000 & streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0"]
