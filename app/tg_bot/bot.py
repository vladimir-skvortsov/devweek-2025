import sys
import os
import logging
from pathlib import Path
from io import BytesIO
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ContentType
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import aiohttp
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.backend.db_client import AirtableClient

load_dotenv()
API_URL = os.getenv('BACKEND_URL', 'http://backend:8000')
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
db = AirtableClient()

class Form(StatesGroup):
    waiting_for_file = State()
    waiting_for_text = State()

# клавиатура после /start
def main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(
        KeyboardButton("📁 Загрузить файл"),
        KeyboardButton("✍️ Ввести текст"),
    )
    return kb

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user = message.from_user
    # создаём пользователя, если нет
    user_id = db.get_user_id_by_tg_id(str(user.id))
    if not user_id:
        rec = db.create_user(tg_id=str(user.id), login=None, password=None)
        logging.info(f"Created new user: {rec}")
    # отправляем меню как reply-клавиатуру
    await message.answer(
        "Добро пожаловать! Выберите действие:",
        reply_markup=main_menu()
    )

# вместо callback_query — просто ловим текст
@dp.message_handler(lambda m: m.text == "📁 Загрузить файл")
async def cmd_upload_file(message: types.Message):
    await message.answer(
        "Пришлите файл для анализа",
        reply_markup=ReplyKeyboardRemove()  # прячем клавиатуру
    )
    await Form.waiting_for_file.set()

@dp.message_handler(lambda m: m.text == "✍️ Ввести текст")
async def cmd_enter_text(message: types.Message):
    await message.answer(
        "Введите текст для анализа",
        reply_markup=ReplyKeyboardRemove()
    )
    await Form.waiting_for_text.set()

# меню для результата
def result_menu(record_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📝 Текст",    callback_data=f"text:{record_id}"),
        InlineKeyboardButton("📊 Score",    callback_data=f"score:{record_id}"),
        InlineKeyboardButton("💡 Explanation", callback_data=f"expl:{record_id}"),
        InlineKeyboardButton("🔢 Tokens",   callback_data=f"tokens:{record_id}"),
    )
    return kb


async def process_analysis(chat_id: int, record_id: str):
    """Присылаем меню с кнопками для просмотра результата"""
    await bot.send_message(chat_id, "Выберите, что показать:", reply_markup=result_menu(record_id))

@dp.message_handler(state=Form.waiting_for_file, content_types=[ContentType.DOCUMENT, ContentType.PHOTO])
async def handle_file(message: types.Message, state: FSMContext):
    await message.answer("Обрабатываем файл...")
    # скачиваем в память
    bio = BytesIO()
    if message.document:
        await message.document.download(destination=bio)
        filename = message.document.file_name
        mime = message.document.mime_type
    else:  # фото
        photo = message.photo[-1]
        await photo.download(destination=bio)
        filename = "photo.jpg"
        mime = "image/jpeg"
    bio.seek(0)

    # отправляем в бэк
    data = aiohttp.FormData()
    data.add_field('file', bio, filename=filename, content_type=mime)
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/api/v1/score/file", data=data) as resp:
            result = await resp.json()

    # сохраняем связь пользователь–запись
    rec = db.create_record(result['text'], result['tokens'], result['explanation'], result['score'])
    record_id = rec['fields']['record_id']
    db.link_user_to_record(user_id=str(message.from_user.id), record_id=record_id)

    await process_analysis(message.chat.id, record_id)
    await state.finish()

@dp.message_handler(state=Form.waiting_for_text, content_types=ContentType.TEXT)
async def handle_text(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await message.answer("Обрабатываем текст...")
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            f"{API_URL}/api/v1/score/text",
            json={"text": text}
        )
        result = await resp.json()
    rec = db.create_record(text, result['tokens'], result['explanation'], result['score'])
    record_id = rec['fields']['record_id']
    db.link_user_to_record(user_id=str(message.from_user.id), record_id=record_id)

    await process_analysis(message.chat.id, record_id)
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith(("score:", "expl:", "tokens:", "text:")))
async def cb_show(cq: types.CallbackQuery):
    action, record_id = cq.data.split(":", 1)
    record = db.get_record_by_id(record_id)
    text = {
        "score":     f"📊 Score: {record['score']}",
        "expl":      f"💡 Explanation:\n{record['explanation']}",
        "tokens":    "🔢 Tokens:\n" + "\n".join([f"{t['token']}: {t['ai_prob']:.3f}" for t in record['tokens']]),
        "text":      f"📝 Текст:\n{record['text']}"
    }[action]

    msg = await bot.send_message(
        cq.message.chat.id,
        text,
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Удалить", callback_data=f"delmsg:{0}")  # placeholder
        )
    )
    # обновим callback_data удаления на правильное message_id
    await bot.edit_message_reply_markup(
        cq.message.chat.id,
        msg.message_id,
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Удалить", callback_data=f"delmsg:{msg.message_id}")
        )
    )
    await cq.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("delmsg:"))
async def cb_delete(cq: types.CallbackQuery):
    _, mid = cq.data.split(":", 1)
    await bot.delete_message(cq.message.chat.id, int(mid))
    await cq.answer()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
