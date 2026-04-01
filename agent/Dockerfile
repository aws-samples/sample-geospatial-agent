FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app

# Install GDAL and build dependencies
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variable to match the installed version
RUN export GDAL_VERSION=$(gdal-config --version)

# Configure UV for container environment
ENV UV_SYSTEM_PYTHON=1 UV_COMPILE_BYTECODE=1

# Install from requirements file
COPY requirements.txt requirements.txt
RUN uv pip install -r requirements.txt

# Signal that this is running in Docker for host binding logic
ENV DOCKER_CONTAINER=1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

# Copy entire project (respecting .dockerignore)
COPY . .

# Use the full module path
CMD ["opentelemetry-instrument", "python", "-m", "geospatial_agent.agent_service"]
