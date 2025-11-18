#!/usr/bin/env python3
"""
Тестовое добавление строки в лист 'КомТехАвто' указанного Google Spreadsheet.

Перед запуском убедитесь, что:
1. В корне проекта лежит файл service-account `google_credentials.json`.
2. Этому сервисному аккаунту предоставлен доступ к документу:
   https://docs.google.com/spreadsheets/d/1f0FkNY39YjnaVTTMfUBaN5JlyDK5ZCzM1MLW_qWnCDI/edit?gid=0#gid=0
3. Виртуальное окружение активировано и зависимости из requirements.txt установлены.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import gspread
from google.oauth2.service_account import Credentials


SHEET_ID = "1f0FkNY39YjnaVTTMfUBaN5JlyDK5ZCzM1MLW_qWnCDI"
WORKSHEET_NAME = "КомТехАвто"
CREDENTIALS_PATH = Path(__file__).parent / "google_credentials.json"

HEADERS: List[str] = [
    "Производитель",
    "Артикул",
    "Код",
    "Наименование",
    "Длина, см",
    "Ширина, см",
    "Высота, см",
    "Вес, кг",
    "Категория",
    "Цена",
    "Остаток",
    "Цена рынок",
    "Название",
    "Описание",
    "Ссылка на главное фото",
    "Ссылки на фото",
    "Цена продажи",
    "Цена до скидки",
]

TEST_ROW: List[str] = [
    "KOMTECHNOLOGY",
    "2905015HF02",
    "KT000001786",
    "Амортизатор передний левый Hongqi H5 II",
    "60",
    "12",
    "12",
    "6",
    "Амортизатор",
    "12000",
    "2",
    "8000",
    "Амортизатор передний левый Hongqi H5 II (стойка подвески передняя левая), 2905015HF02",
    (
        "<h2>Амортизатор передний левый Hongqi H5 II</h2>"
        "<p><strong>Амортизатор передний левый</strong> подходит для автомобилей Hongqi H5 второго поколения. "
        "Обеспечивает эффективную работу подвески и комфорт при движении. "
        "Изготовлен из прочных материалов и полностью совместим с оригинальными креплениями. "
        "Артикул 2905015HF02.</p>"
    ),
    "",
    "",
    "13333",
    "16000",
]


def append_test_row() -> None:
    """Добавляет тестовую строку в лист `КомТехАвто`."""
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"Не найден файл {CREDENTIALS_PATH}. Скопируйте JSON сервисного аккаунта в корень проекта."
        )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_file(str(CREDENTIALS_PATH), scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)
    worksheet = spreadsheet.worksheet(WORKSHEET_NAME)

    existing_headers = worksheet.row_values(1)
    if existing_headers and existing_headers != HEADERS:
        print("⚠️ Заголовки на листе отличаются от ожидаемых, строка всё равно будет добавлена.", file=sys.stderr)
    elif not existing_headers:
        worksheet.append_row(HEADERS, value_input_option="USER_ENTERED")
        print("✅ Добавлены заголовки на лист.")

    worksheet.append_row(TEST_ROW, value_input_option="USER_ENTERED")
    print("🎉 Тестовая строка добавлена. Проверьте лист 'КомТехАвто'.")


if __name__ == "__main__":
    append_test_row()

