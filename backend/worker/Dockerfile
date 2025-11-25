FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy worker requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the worker code
COPY agent_worker.py /app/agent_worker.py

# Expose worker port
EXPOSE 9000

# Run the worker
CMD ["uvicorn", "agent_worker:app", "--host", "0.0.0.0", "--port", "9000"]