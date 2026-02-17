FROM python:3.11-slim

LABEL maintainer="WHALEGOD" \
      description="On-chain whale movement tracker for Solana and Ethereum"

WORKDIR /app

# Install curl for healthchecks, then clean up
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY bot/ ./bot/

# Create data directory and non-root user
RUN mkdir -p /app/data && \
    groupadd -r whalegod && \
    useradd -r -g whalegod -d /app -s /sbin/nologin whalegod && \
    chown -R whalegod:whalegod /app

USER whalegod

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080 9876

CMD ["python", "-m", "bot.main"]
