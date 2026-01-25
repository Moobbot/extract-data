FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (if any needed for Pillow/Pandas)
# RUN apt-get update && apt-get install -y ...

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command (overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
