from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import pytesseract
from PIL import Image
import requests
import sqlite3
import os

# Создание базы для хранения чеков
conn = sqlite3.connect("receipts.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS receipts (
    user_id INTEGER,
    date TEXT,
    inn TEXT,
    total TEXT,
    raw_text TEXT
)
""")
conn.commit()

# OCR + FNS заглушка (можно добавить API ФНС позже)
def extract_check_data(image_path):
    text = pytesseract.image_to_string(Image.open(image_path))
    # Простой пример — ищем сумму
    total_line = next((line for line in text.splitlines() if "сумм" in line.lower()), "Сумма не найдена")
    return text, total_line

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Пришли мне фото чека, и я его проверю.")

# Обработка фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    path = f"check_{update.message.from_user.id}.jpg"
    await photo.download_to_drive(path)

    text, total = extract_check_data(path)

    # Сохраняем чек в базу
    cursor.execute("INSERT INTO receipts (user_id, date, inn, total, raw_text) VALUES (?, ?, ?, ?, ?)",
                   (update.message.from_user.id, "не указано", "не указано", total, text))
    conn.commit()

    os.remove(path)
    await update.message.reply_text(f"Чек распознан. {total}")

# История
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("SELECT total, date FROM receipts WHERE user_id=?", (user_id,))
    records = cursor.fetchall()
    if not records:
        await update.message.reply_text("История пуста.")
    else:
        message = "\n".join([f"{date or 'дата неизвестна'} — {total}" for total, date in records])
        await update.message.reply_text("Вот ваша история:\n" + message)

# Запуск
app = ApplicationBuilder().token("8123657278:AAEjr4NDQPEa9KGSF0jQs2Swj7iH2zkK2ZU").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("history", history))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

app.run_polling()
