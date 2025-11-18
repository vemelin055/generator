#!/usr/bin/env python3
"""
Prosty testowy skrypt: generuje описание через Groq и дописывает его в Google Sheets.

По умолчанию обновляет одну строку, указанную через --row. Если флаг не указан,
обойдет весь лист и заполнит пустые ячейки "Описание".
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from typing import Dict, Optional, List, Tuple

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq


DEFAULT_SHEET_ID = "1f0FkNY39YjnaVTTMfUBaN5JlyDK5ZCzM1MLW_qWnCDI"
DEFAULT_WORKSHEET = "КомТехАвто"
SERVICE_ACCOUNT_FILE = "google_credentials.json"

PROMPT_TEMPLATE = """Ты специалист по автозапчастям и маркетолог. Используй данные:
- Артикул: {article}
- Наименование: {name}
- Название (маркетинговое): {title}

Задача:
1. Напиши структурированное HTML-описание (h2/h3/p/ul/li/strong) на русском языке.
2. Сделай акцент на назначении запчасти, преимуществах, совместимости и установке.
3. Укажи артикул и ключевые выгоды.
4. Объём 90–140 слов. Не добавляй произвольные цены и ссылки.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Генерация описаний через Groq и запись в Google Sheets.")
    parser.add_argument("--sheet-id", default=DEFAULT_SHEET_ID)
    parser.add_argument("--worksheet", default=DEFAULT_WORKSHEET)
    parser.add_argument("--row", type=int, help="Конкретная строка (>=2).")
    parser.add_argument("--start-row", type=int, default=2, help="Начальная строка диапазона (включительно).")
    parser.add_argument("--end-row", type=int, help="Конечная строка диапазона (включительно).")
    parser.add_argument("--dry-run", action="store_true", help="Не записывать в Google Sheets, только выводить.")
    return parser.parse_args()


def get_sheet(sheet_id: str, worksheet: str):
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Не найден {SERVICE_ACCOUNT_FILE}")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id).worksheet(worksheet)


def resolve_columns(header: list[str]) -> Dict[str, int]:
    mapping = {name.strip(): idx + 1 for idx, name in enumerate(header)}
    required = ["Артикул", "Наименование", "Название", "Описание"]
    for key in required:
        if key not in mapping:
            raise RuntimeError(f"В заголовках не найдена колонка '{key}'")
    return mapping


def _is_russian_text(text: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", text or ""))


def generate_description(
    client: Groq,
    article: str,
    name: str,
    title: str,
    retries: int = 3,
) -> Tuple[str, int, int]:
    prompt = PROMPT_TEMPLATE.format(article=article, name=name, title=title or name)
    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        messages = [
            {"role": "system", "content": "Ты пишешь продающие описания автозапчастей. Отвечай только на русском языке."},
            {"role": "user", "content": prompt},
        ]
        if attempt > 1:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Предыдущий ответ был пустой или не на русском. "
                        "Сейчас обязательно верни полный HTML-текст на русском языке."
                    ),
                }
            )

        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.4,
                max_completion_tokens=600,
                top_p=1,
                stream=False,
            )
            text = response.choices[0].message.content.strip()
            usage = response.usage
            prompt_tokens = getattr(usage, "prompt_tokens", 0)
            completion_tokens = getattr(usage, "completion_tokens", 0)
            if text and _is_russian_text(text):
                return text, prompt_tokens, completion_tokens
            last_error = RuntimeError("Пустой или не русскоязычный ответ модели.")
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise RuntimeError(f"Не удалось получить корректное описание: {last_error}")


def process_row(
    sheet,
    row_number: int,
    columns: Dict[str, int],
    client: Groq,
    dry_run: bool = False,
) -> Optional[Tuple[float, int, int]]:
    def get_cell(col_name: str) -> str:
        try:
            value = sheet.cell(row_number, columns[col_name]).value or ""
            return value.strip()
        except Exception:
            return ""

    article = get_cell("Артикул")
    name = get_cell("Наименование")
    title = get_cell("Название") or name

    if not article or not name:
        print(f"⚠️ Строка {row_number}: нет артикула или наименования, пропуск.")
        return None

    print(f"🔧 Генерация для строки {row_number}: {article} | {name}")
    start_time = time.perf_counter()
    description, prompt_tokens, completion_tokens = generate_description(client, article, name, title)

    if dry_run:
        print(description)
    else:
        sheet.update_cell(row_number, columns["Описание"], description)
        print("✅ Записано.")

    duration = time.perf_counter() - start_time
    print(f"⏱️ Время строки: {duration:.2f} c")
    total_tokens = prompt_tokens + completion_tokens
    print(f"   ↳ Токены: prompt={prompt_tokens}, completion={completion_tokens}, всего={total_tokens}")
    return duration, prompt_tokens, completion_tokens


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} c"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)} мин {sec:.0f} c"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{int(hours)} ч {int(minutes)} мин"
    days, hours = divmod(hours, 24)
    return f"{int(days)} д {int(hours)} ч"


def main() -> None:
    args = parse_args()
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY") or os.getenv("QROQ_TOKEN")
    if not api_key:
        raise RuntimeError("В окружении не найден GROQ_API_KEY или QROQ_TOKEN.")

    client = Groq(api_key=api_key)
    sheet = get_sheet(args.sheet_id, args.worksheet)
    header = sheet.row_values(1)
    columns = resolve_columns(header)

    durations: List[float] = []
    prompt_tokens_total = 0
    completion_tokens_total = 0

    processed = 0

    if args.row:
        if args.row < 2:
            raise ValueError("Строка должна быть >= 2 (первая строка — заголовки).")
        result = process_row(sheet, args.row, columns, client, args.dry_run)
        processed = 1 if result is not None else 0
        if result is not None:
            duration, in_tokens, out_tokens = result
            durations.append(duration)
            prompt_tokens_total += in_tokens
            completion_tokens_total += out_tokens
    else:
        rows = sheet.get_all_values()
        for row_number, row_values in enumerate(rows[1:], start=2):
            if row_number < args.start_row:
                continue
            if args.end_row and row_number > args.end_row:
                break

            description = row_values[columns["Описание"] - 1].strip() if len(row_values) >= columns["Описание"] else ""
            if description:
                continue
            result = process_row(sheet, row_number, columns, client, args.dry_run)
            if result is not None:
                duration, in_tokens, out_tokens = result
                processed += 1
                durations.append(duration)
                prompt_tokens_total += in_tokens
                completion_tokens_total += out_tokens

    print(f"🎉 Обработано строк: {processed}")
    if durations:
        avg = sum(durations) / len(durations)
        print(f"📊 Среднее время на строку: {avg:.2f} c")
        estimates = {
            1: avg,
            10: avg * 10,
            100: avg * 100,
            1000: avg * 1000,
            1_000_000: avg * 1_000_000,
        }
        for rows_count, seconds in estimates.items():
            print(f"   • {rows_count} строк: ~{format_duration(seconds)}")
        total_tokens = prompt_tokens_total + completion_tokens_total
        print(
            f"🧮 Токены: prompt={prompt_tokens_total}, completion={completion_tokens_total}, итого={total_tokens}"
        )
    else:
        print("⚠️ Нет успешно обработанных строк для оценки скорости.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Ошибка: {exc}", file=sys.stderr)
        sys.exit(1)

