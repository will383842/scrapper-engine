FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper/ /app/scraper/
COPY config/ /app/config/

# Cron jobs
COPY crontab /etc/cron.d/scraper-cron
RUN chmod 0644 /etc/cron.d/scraper-cron && crontab /etc/cron.d/scraper-cron

EXPOSE 8000

CMD ["uvicorn", "scraper.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
