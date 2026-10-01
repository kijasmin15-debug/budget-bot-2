import os
import gspread
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

SHEET_ID = "1sfnn9K48CnTek05UU8DaBGeBj9dqsd1ctyobgX8X0lo"
SHEET_NAME = "Операции"

CATEGORIES = [
    "❤️ Здоровье",
    "🎉 Досуг",
    "🏠 Дом",
    "☕ Кафе",
    "☕ Кофе",
    "🎁 Подарки",
    "👗 Одежда",
    "🛒 Продукты",
    "👵 Бабушка",
    "🚕 Такси",
    "🐾 Животные",
    "📦 Китайские посылки",
    "💆 Уход",
    "💅 Бьюти процедуры",
    "💰 Сбережения",
    "🧾 Счета",
    "📌 Прочее",
]

user_data = {}


def get_sheet():
    client = gspread.service_account(filename="/app/credentials.json")
    spreadsheet = client.open_by_key(SHEET_ID)
    return spreadsheet.worksheet(SHEET_NAME)


def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["➖ Расход"],
            ["📊 Итоги", "📂 Категории"],
        ],
        resize_keyboard=True,
    )


def categories_keyboard():
    buttons = []

    for i in range(0, len(CATEGORIES), 2):
        buttons.append(CATEGORIES[i:i + 2])

    buttons.append(["↩️ Отмена"])

    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.pop(update.effective_user.id, None)

    await update.message.reply_text(
        "Привет! 😊\n\nВыбери действие кнопкой ниже:",
        reply_markup=main_keyboard(),
    )


async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📂 Выбери категорию:",
        reply_markup=categories_keyboard(),
    )


async def expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_user.id] = {"action": "expense"}

    await update.message.reply_text(
        "📂 Выбери категорию:",
        reply_markup=categories_keyboard(),
    )


async def totals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        current_month = datetime.now().strftime("%m.%Y")
        total_expense = 0

        for row in records:
            date_value = str(row.get("Дата", ""))

            if date_value.endswith(current_month):
                try:
                    total_expense += float(row.get("Расход", 0) or 0)
                except (ValueError, TypeError):
                    pass

        await update.message.reply_text(
            f"📊 Итоги за {current_month}\n\n"
            f"Расходы: {total_expense:.2f}"
        )

    except Exception as e:
        print(f"Ошибка итогов: {e}")
        await update.message.reply_text(
            "😔 Не удалось получить данные из таблицы."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "➖ Расход":
        await expense_start(update, context)
        return

    if text == "📊 Итоги":
        await totals(update, context)
        return

    if text == "📂 Категории":
        await categories(update, context)
        return

    if text == "↩️ Отмена":
        user_data.pop(user_id, None)
        await update.message.reply_text(
            "Отменено.",
            reply_markup=main_keyboard(),
        )
        return

    data = user_data.get(user_id)

    if not data:
        return

    if data.get("action") == "expense" and "category" not in data:
        if text not in CATEGORIES:
            await update.message.reply_text(
                "Пожалуйста, выбери категорию кнопкой."
            )
            return

        data["category"] = text

        await update.message.reply_text(
            "💰 Теперь введи сумму:"
        )
        return

    if data.get("action") == "expense" and "amount" not in data:
        try:
            amount = float(text.replace(",", "."))
            data["amount"] = amount

            await update.message.reply_text(
                "📝 Напиши описание.\n\n"
                "Если описание не нужно — напиши: -"
            )

        except ValueError:
            await update.message.reply_text(
                "Введите сумму числом, например: 500"
            )

        return

    if data.get("action") == "expense" and "amount" in data:
        description = "" if text == "-" else text

        try:
            sheet = get_sheet()
            today = datetime.now().strftime("%d.%m.%Y")

            sheet.append_row(
                [
                    today,
                    data["category"],
                    description,
                    "",
                    data["amount"],
                ]
            )

            await update.message.reply_text(
                "✅ Записала в таблицу!",
                reply_markup=main_keyboard(),
            )

            user_data.pop(user_id, None)

        except Exception as e:
            print(f"Ошибка записи: {e}")

            await update.message.reply_text(
                "😔 Не удалось записать данные в таблицу."
            )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        print("Токен Telegram не найден!")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Второй бот запущен!")

    app.run_polling()


if __name__ == "__main__":
    main()
