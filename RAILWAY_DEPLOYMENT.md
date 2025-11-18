# Railway Deployment Guide

This guide explains how to deploy the Description Generator application on Railway.

## Prerequisites
- A Railway account (https://railway.app)
- GitHub repository connected to Railway
- Google Service Account credentials for Google Sheets API

## Environment Variables for Railway

Set the following environment variables in your Railway project dashboard:

### Required Variables:
- `PORT`: Set to `5000` (Railway automatically assigns a port, but the app uses this)
- `FLASK_DEBUG`: Set to `0` for production

### Google Sheets Credentials (Required):
- `GOOGLE_CREDENTIALS_JSON`: Paste the entire JSON content of your Google service account credentials
- OR `GOOGLE_CREDENTIALS_BASE64`: Base64 encoded version of the JSON credentials

### Optional AI/API Tokens (if used):
- `QROQ_TOKEN`: For Groq API access
- `OPENROUTER_API_KEY`: For OpenRouter API access
- `APIFY_TOKEN`: For Apify service
- `YOUTUBE_API_KEY`: For YouTube Data API

### Other Optional Variables (from .env):
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `YANDEX_DISK_TOKEN`
- `YANDEX_CLIENT_ID`
- `YANDEX_CLIENT_SECRET`
- `VK_TOKEN`
- And others as needed

## Deployment Steps

1. **Connect Repository**: Connect your GitHub repository to Railway
2. **Set Environment Variables**: Add all required environment variables in Railway dashboard
3. **Deploy**: Railway will automatically detect the Dockerfile and deploy
4. **Access**: Your app will be available at the provided Railway URL

## Important Notes

- The application uses `credentials_util.py` to handle Google credentials
- Credentials can be provided via:
  - `GOOGLE_CREDENTIALS_JSON` environment variable (raw JSON)
  - `GOOGLE_CREDENTIALS_BASE64` environment variable (base64 encoded JSON)
  - Or by including `google_credentials.json` in the repository (not recommended for security)

- For production, ensure `FLASK_DEBUG=0`
- The Dockerfile uses Gunicorn as the production server
- Railway automatically handles SSL certificates

## Local Development with Docker

You can test the Docker setup locally:
```bash
docker build -t description-generator .
docker run -p 5000:5000 -e FLASK_DEBUG=0 description-generator
```

Or with docker-compose:
```bash
docker-compose up
```

## Troubleshooting

- Check Railway logs for any deployment issues
- Ensure all required environment variables are set
- Verify Google Sheets API access with your service account
