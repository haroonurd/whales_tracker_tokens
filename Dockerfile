FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy monitor files
COPY whales_monitor.py .
COPY config.example.py .

# Run (expects a config.py via volume or env)
CMD ["python", "whales_monitor.py"]
