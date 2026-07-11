# Use a slim Python image
FROM python:3.11-slim

# Install system dependencies for PostgreSQL and OpenSSL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

RUN mkdir -p /app/database && chmod 777 /app/database

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# RUN sed -i 's/\r$//' /app/boot.sh && \
#     chmod +x /app/boot.sh
#
# CMD ["/bin/bash", "/app/boot.sh"]
