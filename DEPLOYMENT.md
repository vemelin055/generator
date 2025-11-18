# Railway Deployment Guide

This project is ready to run on [Railway](https://railway.app/) with the
provided `Procfile` (`web: gunicorn app:app --bind 0.0.0.0:${PORT:-5001}`).
Follow these steps to bootstrap the service and configure secrets.

## 1. Create a Railway project

1. Install the CLI: `npm i -g @railway/cli`
2. Log in: `railway login`
3. Inside the repository root run `railway init`
4. Deploy from the CLI (`railway up`) or connect the GitHub repo in the UI

## 2. Configure the start command

Railway automatically uses `Procfile` if present. Alternatively set the
start command manually to:

```
gunicorn app:app --bind 0.0.0.0:$PORT
```

`gunicorn` is listed in `requirements.txt`, so Railway installs it during
the build phase.

## 3. Environment variables

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

## 4. Railway-specific behavior

- Flask now binds to `0.0.0.0` using the injected `PORT`, so Railway can
  route traffic to the container.
- When running outside the WSGI server (e.g., local `python app.py`),
  `FLASK_DEBUG=1` automatically re-enables the debug reloader.
- `credentials_util.ensure_google_credentials_file()` ensures the Google
  service account is available both locally (from the JSON file) and on
  Railway (via env vars).

## 5. Local testing vs. Railway

```
# Local dev
pip install -r requirements.txt
FLASK_DEBUG=1 python app.py

# Railway preview (same command the platform runs)
gunicorn app:app --bind 0.0.0.0:5001
```

If you use `.env` locally, Railway variables override those values.

---

Once the variables are configured, each deploy automatically runs the
Gunicorn server and the GUI will be available on the Railway-generated URL.

