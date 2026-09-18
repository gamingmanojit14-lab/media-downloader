FROM python:3.11-slim

WORKDIR /app

# ffmpeg, Node.js (JS runtime), এবং curl ইনস্টল
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# YouTube bot detection bypass-এর জন্য POT provider
RUN pip install bgutil-ytdlp-pot-provider

COPY . .

EXPOSE 5000

CMD gunicorn --bind 0.0.0.0:5000 --timeout 120 app:app
