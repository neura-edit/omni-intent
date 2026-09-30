# OmniIntent Decision Engine
FROM python:3.11-slim

WORKDIR /app

# Copy application files
COPY app.py config.json ./
COPY assets/ ./assets/

# Expose standard HTTP port
EXPOSE 8080

# Run engine
CMD ["python3", "-u", "app.py"]
