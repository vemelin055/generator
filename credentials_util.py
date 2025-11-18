"""
Helpers for managing Google service-account credentials in different environments.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Optional


DEFAULT_CREDENTIALS_PATH = Path("google_credentials.json")


def ensure_google_credentials_file(
    destination: Optional[str | os.PathLike] = None,
) -> Path:
    """
    Ensure that the Google service-account credentials file exists on disk.

    Priority:
      1. Existing file on disk (nothing to do)
      2. Environment variable GOOGLE_CREDENTIALS_JSON containing raw JSON
      3. Environment variable GOOGLE_CREDENTIALS_BASE64 containing base64 of the JSON

    Raises:
        FileNotFoundError: if no file exists and no environment variable is provided.
        ValueError: if the base64 payload cannot be decoded.
        json.JSONDecodeError: if provided JSON is invalid.
    """

    dest_path = Path(destination) if destination else DEFAULT_CREDENTIALS_PATH
    if dest_path.exists():
        return dest_path

    raw_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not raw_json:
        b64_payload = os.getenv("GOOGLE_CREDENTIALS_BASE64")
        if b64_payload:
            try:
                raw_json = base64.b64decode(b64_payload).decode("utf-8")
            except Exception as exc:  # noqa: BLE001
                raise ValueError(
                    "Не удалось декодировать GOOGLE_CREDENTIALS_BASE64"
                ) from exc

    if not raw_json:
        raise FileNotFoundError(
            "Не найден файл google_credentials.json. "
            "Установите переменную окружения GOOGLE_CREDENTIALS_JSON или GOOGLE_CREDENTIALS_BASE64."
        )

    # Validate JSON before writing to disk
    json.loads(raw_json)
    dest_path.write_text(raw_json, encoding="utf-8")
    return dest_path


__all__ = ["ensure_google_credentials_file", "DEFAULT_CREDENTIALS_PATH"]

