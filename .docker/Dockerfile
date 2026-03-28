# sync_worker/Dockerfile
FROM python:3.12-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    libgomp1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir PyYAML

# Install llama-cpp-python from pre-built wheel if available, otherwise skip for now
# We'll handle this in the requirements.txt or install it conditionally
RUN pip install --no-cache-dir -r requirements.txt

COPY homeschool/ ./homeschool/

COPY config.yaml .

CMD ["python", "-m", "homeschool", "sync"]

