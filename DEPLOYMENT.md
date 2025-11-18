# Railway Deployment Guide

This project is ready to run on [Railway](https://railway.app/) using Docker.
The Dockerfile is configured for production deployment with Gunicorn.
Follow these steps to bootstrap the service and configure secrets.

## 1. Quick Start

1. Connect your GitHub repository to Railway
2. Railway will auto-detect the Dockerfile
3. **IMPORTANT**: Set the required environment variables (see below)
4. Deploy!

## 2. Environment variables

Create the following variables in the Railway dashboard (Project →
Variables). All values are stored server-side and exposed to the runtime.

**⚠️ CRITICAL**: You MUST set `GOOGLE_CREDENTIALS_JSON` or `GOOGLE_CREDENTIALS_BASE64` 
or you will see this error:
```
Не найден файл google_credentials.json. Установите переменную окружения GOOGLE_CREDENTIALS_JSON или GOOGLE_CREDENTIALS_BASE64.
```

| Variable | Required | Description |
| --- | --- | --- |
| `PORT` | no | Railway injects this automatically; only override locally |
| `FLASK_DEBUG` | no | Set to `0` in production (default). `1` enables debug logs |
| `SECRET_KEY` | recommended | Secret key for Flask sessions (auto-generated if not set) |
| `ADMIN_EMAIL` | recommended | Admin login email (default: vemelin055@gmail.com) |
| `ADMIN_PASSWORD` | recommended | Admin login password (default: Emelin12) |
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

**🔒 Security Note**: For production deployments, it's **strongly recommended** to set:
- `ADMIN_EMAIL` - Your admin email address
- `ADMIN_PASSWORD` - A strong, unique password
- `SECRET_KEY` - A random secret key for session encryption

If not set, default credentials will be used (not secure for production).

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
