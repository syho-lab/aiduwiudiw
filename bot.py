import os
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI
from docx import Document

# -----------------------
# Конфигурация
# -----------------------
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# Хранение контекста каждой книги у пользователей
user_histories = {}

# -----------------------
# Функции
# -----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь тему книги или 'Продолжить:' + последний абзац, чтобы продолжить книгу."
    )

def generate_text(messages):
    """Вызывает Olmo 3.1 Think и возвращает текст с reasoning"""
    response = client.chat.completions.create(
        model="allenai/olmo-3.1-32b-think:free",
        messages=messages,
        extra_body={"reasoning": {"enabled": True}}
    )
    return response.choices[0].message

def create_word_file(text, filename="book.docx"):
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(filename)
    return filename

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    prompt = update.message.text

    await update.message.reply_text("Генерирую текст, это может занять минуту...")

    # Получаем историю пользователя или создаём новую
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": prompt})

    # Генерация текста
    response_msg = generate_text(history)

    # Добавляем ответ в историю
    history.append({
        "role": "assistant",
        "content": response_msg.content,
        "reasoning_details": getattr(response_msg, "reasoning_details", None)
    })

    # Сохраняем обновлённую историю
    user_histories[user_id] = history

    # Создаём Word файл
    filename = create_word_file(response_msg.content)

    # Отправляем файл пользователю
    with open(filename, "rb") as f:
        await update.message.reply_document(InputFile(f, filename=filename))

# -----------------------
# Запуск бота
# -----------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print("Бот запущен...")
    app.run_polling()
