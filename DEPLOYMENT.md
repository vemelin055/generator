# Railway Deployment Guide

This project is ready to run on [Railway](https://railway.app/) using Docker.
The Dockerfile is configured for production deployment with Gunicorn.
Follow these steps to bootstrap the service and configure secrets.

## 2. Environment variables

Create the following variables in the Railway dashboard (Project →
Variables). All values are stored server-side and exposed to the runtime.

| Variable | Required | Description |
| --- | --- | --- |
| `PORT` | no | Railway injects this automatically; only override locally |
| `FLASK_DEBUG` | no | Set to `0` in production (default). `1` enables debug logs |
| `GROQ_API_KEY` | yes | API key for Groq models (or use legacy `QROQ_TOKEN`) |
| `OPENROUTER_API_KEY` | optional | Enables DeepSeek fallback via OpenRouter |
| `OPENROUTER_REFERER` | optional | Custom referer header for OpenRouter |
| `OPENROUTER_APP_TITLE` | optional | Custom app title header for OpenRouter |
| `GOOGLE_CREDENTIALS_JSON` | yes* | Paste the full service-account JSON |
| `GOOGLE_CREDENTIALS_BASE64` | alternative | Base64-encoded JSON; used when the plaintext variable is unavailable |
| `GOOGLE_CREDENTIALS_FILE` | optional | Custom path for the generated credentials file |

\* Either `GOOGLE_CREDENTIALS_JSON` **or** `GOOGLE_CREDENTIALS_BASE64`
must be supplied. The application writes the JSON to
`google_credentials.json` at runtime if it does not exist.

## 3. Railway Deployment

Railway will automatically detect and use the Dockerfile for deployment.
The Dockerfile is configured to:
- Use Python 3.11-slim base image
- Set up a secure non-root user
- Install dependencies from requirements.txt
- Expose port 5000
- Run with Gunicorn production server

## 4. Local testing vs. Railway

```
# Local dev with Docker
docker-compose up

# Or build and run directly
docker build -t description-generator .
docker run -p 5000:5000 -e FLASK_DEBUG=0 description-generator

# Local dev without Docker
pip install -r requirements.txt
FLASK_DEBUG=1 python app.py
```

If you use `.env` locally, Railway variables override those values.

---

Once the variables are configured, each deploy automatically runs the
Gunicorn server and the GUI will be available on the Railway-generated URL.
