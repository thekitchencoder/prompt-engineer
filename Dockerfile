# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY prompt_engineer/ ./prompt_engineer/
COPY pyproject.toml .
COPY README.md .
COPY CLAUDE.md .

# Install the application
RUN pip install -e .

# Create directories for configs and workspace
RUN mkdir -p /workspace /root/.prompt-engineer

# Expose Gradio default port
EXPOSE 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["prompt-engineer", "--workspace", "/workspace", "--port", "7860"]
