import logging
import os
import sys
from io import BytesIO
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (ContentType, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.backend.db_client import AirtableClient

load_dotenv()
API_URL = os.getenv('BACKEND_URL', 'http://backend:8000')
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise RuntimeError('TELEGRAM_TOKEN is not set')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
db = AirtableClient()


class Form(StatesGroup):
    waiting_for_file = State()
    waiting_for_text = State()


def main_menu() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton('📁 Загрузить файл'),
        KeyboardButton('✍️ Ввести текст'),
    )
    return kb


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user = message.from_user
    user_id = db.get_user_id_by_tg_id(str(user.id))
    if not user_id:
        rec = db.create_user(tg_id=str(user.id), login=None, password=None)
        logging.info(f'Created new user: {rec}')

    await message.answer(
        'Добро пожаловать! Выберите действие:',
        reply_markup=main_menu()
    )


@dp.message_handler(lambda m: m.text == '📁 Загрузить файл')
async def cmd_upload_file(message: types.Message):
    await message.answer(
        'Пришлите файл для анализа',
        reply_markup=ReplyKeyboardRemove()
    )
    await Form.waiting_for_file.set()


@dp.message_handler(lambda m: m.text == '✍️ Ввести текст')
async def cmd_enter_text(message: types.Message):
    await message.answer(
        'Введите текст для анализа',
        reply_markup=ReplyKeyboardRemove()
    )
    await Form.waiting_for_text.set()


def result_menu(record_id: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton('📝 Текст', callback_data=f'text:{record_id}'),
        InlineKeyboardButton('💡 Объяснение', callback_data=f'expl:{record_id}'),
        InlineKeyboardButton('🔢 Токены', callback_data=f'tokens:{record_id}'),
        InlineKeyboardButton('📊 Рекомендации', callback_data=f'examp:{record_id}'),
    )
    return kb


async def process_analysis(chat_id: int, score: float, record_id: str):
    score = round(score * 100, 1)
    await bot.send_message(chat_id, f'Оценка: {score}%.\nВыберите, что показать:', reply_markup=result_menu(record_id))


SUPPORTED_MIMES = {
    'application/pdf',
    'text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
    'image/png',
    'image/jpeg',
}
SUPPORTED_EXT = {'pdf', 'txt', 'docx', 'pptx', 'png', 'jpg', 'jpeg'}


@dp.message_handler(state=Form.waiting_for_file, content_types=[ContentType.DOCUMENT, ContentType.PHOTO])
async def handle_file(message: types.Message, state: FSMContext):
    await message.answer('Обрабатываем файл...', reply_markup=ReplyKeyboardRemove())

    bio = BytesIO()
    if message.document:
        filename = message.document.file_name
        mime = message.document.mime_type
        ext = filename.rsplit('.', 1)[-1].lower()
        if mime not in SUPPORTED_MIMES or ext not in SUPPORTED_EXT:
            await message.answer(
                '❌ Неподдерживаемый формат.\n'
                f'Поддерживаемые типы: {", ".join(sorted(SUPPORTED_EXT))}',
                reply_markup=main_menu()
            )
            return await state.finish()
        await message.document.download(destination_file=bio)
    elif message.photo:
        photo = message.photo[-1]
        await photo.download(destination_file=bio)
        filename = 'photo.jpg'
        mime = 'image/jpeg'
    else:
        await message.answer(
            'Пожалуйста, пришлите файл формата PDF, DOCX, TXT или изображение.',
            reply_markup=main_menu()
        )
        return await state.finish()
    bio.seek(0)

    data = aiohttp.FormData()
    data.add_field('file', bio, filename=filename, content_type=mime)
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{API_URL}/api/v1/score/file', data=data) as resp:
            result = await resp.json()

    if result.get('text', 0) == 0:
        await bot.send_message(
            message.chat.id,
            'Ошибка при разборе. Повторите запрос',
            reply_markup=main_menu()
        )

        await state.finish()
    rec = db.create_record(result['text'], result['tokens'], result['explanation'], result['score'],
                           result['examples'])
    record_id = rec['fields']['record_id']

    id = str(db.get_user_id_by_tg_id(message.from_user.id))
    db.link_user_to_record(user_id=id, record_id=record_id)

    await process_analysis(message.chat.id, result['score'], record_id)
    await bot.send_message(
        message.chat.id,
        'Готов к использованию 😃',
        reply_markup=main_menu()
    )

    await state.finish()


@dp.message_handler(state=Form.waiting_for_text, content_types=ContentType.TEXT)
async def handle_text(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await message.answer('Обрабатываем текст...', reply_markup=ReplyKeyboardRemove())
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            f'{API_URL}/api/v1/score/text',
            json={'text': text, 'models': ['gpt', 'claude']}
        )
        result = await resp.json()
    rec = db.create_record(text, result['tokens'], result['explanation'], result['score'], result['examples'])
    record_id = rec['fields']['record_id']

    id = str(db.get_user_id_by_tg_id(message.from_user.id))
    db.link_user_to_record(user_id=str(id), record_id=record_id)

    await process_analysis(message.chat.id, result['score'], record_id)
    await bot.send_message(
        message.chat.id,
        'Готов к использованию 😃',
        reply_markup=main_menu()
    )

    await state.finish()


@dp.callback_query_handler(lambda c: c.data.startswith(('text:', 'expl:', 'tokens:', 'examp:')))
async def cb_show(cq: types.CallbackQuery):
    action, record_id = cq.data.split(':', 1)
    record = db.get_record_by_id(record_id)
    tokens = [
        t for t in record['tokens']
        if len(t['token']) >= 3 and t['ai_prob'] > 0.4 and not set('#,.').intersection(t['token'])
    ]
    text = {
        'text': f'📝 Текст:\n{record["text"]}',
        'expl': f'💡 Объяснение:\n{record["explanation"]}',
        'tokens': '🔢 Токены:\n' + '\n'.join([f'{t["token"]}: {t["ai_prob"]:.3f}' for t in tokens]),
        'examp': f'💡 Рекомендации:\n{record["examples"]}',
    }[action]

    msg = await bot.send_message(
        cq.message.chat.id,
        text,
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton('❌ Удалить', callback_data=f'delmsg:{0}')
        )
    )

    await bot.edit_message_reply_markup(
        cq.message.chat.id,
        msg.message_id,
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton('❌ Удалить', callback_data=f'delmsg:{msg.message_id}')
        )
    )
    await cq.answer()


@dp.callback_query_handler(lambda c: c.data.startswith('delmsg:'))
async def cb_delete(cq: types.CallbackQuery):
    _, mid = cq.data.split(':', 1)
    await bot.delete_message(cq.message.chat.id, int(mid))
    await cq.answer()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
