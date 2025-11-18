#!/usr/bin/env python3
"""
Автогенерация описаний (колонка `Описание`) в листе Google Sheets `КомТехАвто`.

Скрипт использует модель `openai/gpt-oss-120b` через токен `QROQ_TOKEN`
из `.env`, а также сервисный аккаунт Google (`google_credentials.json`).

Пример запуска:
    source .venv/bin/activate
    pip install -r requirements.txt
    python generate_descriptions.py --limit 10
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq
from groq import GroqError
import requests
from credentials_util import (
    DEFAULT_CREDENTIALS_PATH,
    ensure_google_credentials_file,
)


DEFAULT_SHEET_ID = "1f0FkNY39YjnaVTTMfUBaN5JlyDK5ZCzM1MLW_qWnCDI"
DEFAULT_WORKSHEET = "КомТехАвто"
SERVICE_ACCOUNT_FILE = os.environ.get(
    "GOOGLE_CREDENTIALS_FILE", str(DEFAULT_CREDENTIALS_PATH)
)


PROMPT_TEMPLATE = """Ты специалист по автозапчастям и маркетолог. Используй данные:
- Артикул: {article}
- Наименование: {name}

Задача:
1. Напиши структурированное HTML-описание (h2/h3/p/ul/li/strong) на русском языке.
2. Сделай акцент на назначении запчасти, преимуществах, совместимости и установке.
3. Укажи артикул и ключевые выгоды.
4. Объём 90–140 слов. Не добавляй произвольные цены и ссылки.
"""


@dataclass
class SheetColumns:
    article: int
    name: int
    description: int


class DescriptionGenerator:
    def __init__(
        self,
        sheet_id: str,
        worksheet_name: str,
        force: bool = False,
        dry_run: bool = False,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        log_level: str = "INFO",
    ):
        load_dotenv()
        self.sheet_id = self._normalize_sheet_id(sheet_id)
        self.worksheet_name = worksheet_name
        self.force = force
        self.dry_run = dry_run
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s | %(levelname)s | %(message)s",
        )
        self.logger = logging.getLogger("generate_descriptions")

        self.client = self._init_llm_client()
        self.sheet = self._init_sheet()
        self.columns = self._resolve_columns()

    @staticmethod
    def _normalize_sheet_id(sheet_input: str) -> str:
        if not sheet_input:
            raise RuntimeError("Не указан ID таблицы или ссылка на Google Sheets.")
        if "spreadsheets/d/" in sheet_input:
            return sheet_input.split("/d/")[1].split("/")[0]
        return sheet_input

    def _init_llm_client(self) -> Groq:
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("QROQ_TOKEN")
        if not api_key:
            raise RuntimeError("В .env отсутствует GROQ_API_KEY или QROQ_TOKEN")

        client = Groq(api_key=api_key)
        self.logger.info("Используется Groq модель 'openai/gpt-oss-120b'")
        return client

    def _init_sheet(self):
        ensure_google_credentials_file(SERVICE_ACCOUNT_FILE)
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(
                f"Не найден '{SERVICE_ACCOUNT_FILE}'. "
                "Укажите GOOGLE_CREDENTIALS_JSON/GOOGLE_CREDENTIALS_BASE64 в Railway."
            )

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(self.sheet_id)
        return spreadsheet.worksheet(self.worksheet_name)

    def _resolve_columns(self) -> SheetColumns:
        header = self.sheet.row_values(1)
        header_map: Dict[str, int] = {name.strip(): idx + 1 for idx, name in enumerate(header)}

        try:
            return SheetColumns(
                article=header_map["Артикул"],
                name=header_map["Наименование"],
                description=header_map["Описание"],
            )
        except KeyError as exc:
            raise RuntimeError(
                f"Не найдена колонка '{exc.args[0]}' в первой строке. Проверьте заголовки."
            )

    def _build_prompt(self, article: str, name: str) -> str:
        return PROMPT_TEMPLATE.format(article=article.strip(), name=name.strip())

    def _is_russian_text(self, text: str) -> bool:
        return bool(re.search(r"[А-Яа-яЁё]", text or ""))

    def _generate_description(self, article: str, name: str) -> str:
        prompt = self._build_prompt(article, name)
        models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]
        last_error: Optional[Exception] = None

        for model_idx, model_name in enumerate(models):
            self.logger.info("Попытка использования модели: %s", model_name)

            for attempt in range(1, self.max_retries + 1):
                try:
                    self.logger.debug("LLM request attempt %s for article %s with model %s", attempt, article, model_name)
                    messages = [
                        {"role": "system", "content": "Ты пишешь продающие описания автозапчастей. Используй только русский язык."},
                        {"role": "user", "content": prompt},
                    ]
                    if attempt > 1:
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "Предыдущий ответ был пустой или не на русском. "
                                    "Сейчас обязательно верни развёрнутое описание на русском языке."
                                ),
                            }
                        )

                    completion = self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=0.4,
                        max_completion_tokens=900,
                        top_p=1,
                        stream=True,
                    )
                    parts: List[str] = []
                    try:
                        for chunk in completion:
                            delta = chunk.choices[0].delta
                            if not delta:
                                continue
                            content = getattr(delta, "content", None)
                            if not content:
                                continue

                            if isinstance(content, list):
                                for piece in content:
                                    if isinstance(piece, str):
                                        parts.append(piece)
                                    elif isinstance(piece, dict) and piece.get("type") == "text":
                                        parts.append(piece.get("text", ""))
                            elif isinstance(content, str):
                                parts.append(content)
                    except GeneratorExit:
                        self.logger.debug("Поток завершён (GeneratorExit) для %s", article)

                    text = "".join(parts).strip()
                    # Remove markdown code block formatting if present
                    text = text.removeprefix("```html").removesuffix("```").strip()
                    if not text or not self._is_russian_text(text):
                        raise RuntimeError("Пустой или не русскоязычный ответ модели.")
                    
                    self.logger.info("✅ Успешно сгенерировано с использованием модели: %s", model_name)
                    return text

                except GroqError as exc:
                    last_error = exc
                    self.logger.warning("GroqError (%s/%s, модель %s): %s", attempt, self.max_retries, model_name, exc)
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    self.logger.exception("Неожиданная ошибка LLM (%s/%s, модель %s): %s", attempt, self.max_retries, model_name, exc)
                    break

                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

            if model_idx < len(models) - 1:
                self.logger.warning("Модель %s не сработала, пробую следующую модель...", model_name)
                time.sleep(self.retry_delay)
            else:
                self.logger.warning(
                    "Все модели Groq (%s) не ответили (последняя ошибка: %s). "
                    "Пробую DeepSeek через OpenRouter...",
                    ", ".join(models),
                    last_error,
                )
                return self._generate_with_openrouter(prompt)

        raise RuntimeError("Не удалось получить ответ от LLM")

    def _generate_with_openrouter(self, prompt: str) -> str:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Не удалось получить ответ от Groq и не указан OpenRouter API ключ "
                "(переменная окружения OPENROUTER_API_KEY)."
            )

        referer = os.getenv("OPENROUTER_REFERER", "https://github.com/user/generate_description")
        app_title = os.getenv("OPENROUTER_APP_TITLE", "Description Generator")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": referer,
            "X-Title": app_title,
        }

        payload = {
            "model": "deepseek/deepseek-chat-v3.1",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты пишешь продающие описания автозапчастей. Используй только русский язык.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 900,
        }

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
        except requests.RequestException as exc:  # noqa: BLE001
            raise RuntimeError(f"Ошибка запроса к OpenRouter: {exc}") from exc

        if response.status_code >= 400:
            raise RuntimeError(
                f"OpenRouter вернул статус {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenRouter вернул пустой список choices.")

        message = choices[0].get("message") or {}
        text = (message.get("content") or "").strip()
        text = text.removeprefix("```html").removesuffix("```").strip()

        if not text or not self._is_russian_text(text):
            raise RuntimeError("OpenRouter/DeepSeek вернул пустой ответ или не на русском языке.")

        self.logger.info("✅ Успешно сгенерировано через DeepSeek (OpenRouter).")
        return text

    def process(
        self,
        start_row: int = 2,
        end_row: Optional[int] = None,
        limit: Optional[int] = None,
        sleep: float = 0.0,
    ) -> int:
        rows = self.sheet.get_all_values()
        processed = 0
        total_time = 0.0

        for idx, row in enumerate(rows, start=1):
            if idx < start_row:
                continue
            if end_row and idx > end_row:
                break

            article = row[self.columns.article - 1].strip() if len(row) >= self.columns.article else ""
            name = row[self.columns.name - 1].strip() if len(row) >= self.columns.name else ""
            description = (
                row[self.columns.description - 1].strip()
                if len(row) >= self.columns.description
                else ""
            )

            if not article or not name:
                continue

            if description and not self.force:
                continue

            self.logger.info("🔧 Строка %s | %s | %s", idx, article, name)
            request_start = time.perf_counter()
            try:
                text = self._generate_description(article, name)
            except RuntimeError as exc:
                self.logger.error("❌ Ошибка генерации для строки %s: %s", idx, exc)
                continue
            request_time = time.perf_counter() - request_start
            total_time += request_time

            if self.dry_run:
                self.logger.info("📝 (dry-run) %s", text[:100].replace("\n", " ") + "...")
            else:
                try:
                    self.sheet.update_cell(idx, self.columns.description, text)
                    self.logger.info("✅ Записано в Google Sheets.")
                except Exception as exc:  # noqa: BLE001
                    self.logger.error("❌ Не удалось обновить строку %s: %s", idx, exc)
                    continue

            self.logger.info("⏱️ Время запроса: %.2f c", request_time)

            processed += 1

            if limit and processed >= limit:
                break

            if sleep:
                time.sleep(sleep)

        if processed:
            avg = total_time / processed
            self.logger.info("📊 Среднее время: %.2f c (обработано %s)", avg, processed)
            self.logger.info("⏲️ Всего времени LLM: %.2f c", total_time)

        return processed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Генерация описаний товаров для листа Google Sheets.")
    parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID, help="ID таблицы Google.")
    parser.add_argument("--worksheet", default=DEFAULT_WORKSHEET, help="Название листа.")
    parser.add_argument("--limit", type=int, help="Максимум строк для обработки за запуск.")
    parser.add_argument("--start-row", type=int, default=2, help="Номер строки, с которой начинать (включительно).")
    parser.add_argument("--end-row", type=int, help="Номер строки, на которой остановиться (включительно).")
    parser.add_argument("--max-retries", type=int, default=3, help="Количество повторов при ошибках LLM.")
    parser.add_argument("--retry-delay", type=float, default=2.0, help="Пауза между ретраями (сек).")
    parser.add_argument("--log-level", default="INFO", help="Уровень логирования (DEBUG/INFO/WARNING/ERROR).")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Перезаписывать уже заполненные описания.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Не записывать в таблицу, только печатать.")
    parser.add_argument("--sleep", type=float, default=0.0, help="Пауза между запросами (сек).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    normalized_sheet_id = DescriptionGenerator._normalize_sheet_id(args.sheet_id)
    try:
        generator = DescriptionGenerator(
            sheet_id=normalized_sheet_id,
            worksheet_name=args.worksheet,
            force=args.force,
            dry_run=args.dry_run,
            max_retries=args.max_retries,
            retry_delay=args.retry_delay,
            log_level=args.log_level,
        )
        count = generator.process(
            start_row=args.start_row,
            end_row=args.end_row,
            limit=args.limit,
            sleep=args.sleep,
        )
        print(f"🎉 Обработано строк: {count}")
    except Exception as exc:
        print(f"❌ Ошибка: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
