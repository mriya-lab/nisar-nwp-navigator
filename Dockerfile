FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY .streamlit/config.toml .streamlit/config.toml
COPY app/ app/
COPY pipeline/ pipeline/
COPY data/gis/ data/gis/
COPY data/processed/ data/processed/

EXPOSE 8501
HEALTHCHECK --start-period=15s CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).close()"]
CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
