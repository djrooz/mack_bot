import asyncio
import random
import os
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    FSInputFile,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logging.info("🚀 Starting bot...")


# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_FOLDER = os.path.join(BASE_DIR, "cards")


# ================= RENDER DUMMY SERVER =================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_dummy_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    logging.info(f"🌐 Dummy server running on port {port}")
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()
# ======================================================


# ================= ENV =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
assert BOT_TOKEN, "❌ BOT_TOKEN is missing"

ADMIN_CHAT_ID = 6567991779  # Telegram ID Анжелы


# ================= TEXT =================
CONTACT_TEXT = (
    "✨ Если хочешь глубже разобрать свой запрос,\n"
    "Анжела проводит индивидуальные MAC-сессии.\n\n"
    "👤 Анжела Цой\n"
    "📞 +996 551 040 832\n"
    "📸 Instagram: @anjela_tsoy_psy\n"
    "💬 Telegram: @anjela_tsoy"
)

QUESTIONS = [
    "1. Что ты первым заметил(а) на карте?",
    "2. Какие эмоции вызывает эта карта?",
    "3. Есть ли на карте персонаж? Кто он для тебя?",
    "4. Что на карте похоже на твою ситуацию?",
    "5. Что на карте тебе не нравится или напрягает?",
    "6. Где на карте ты, если представить себя внутри?",
    "7. Чего не хватает на карте?",
    "8. Что бы ты хотел(а) изменить на карте?",
    "9. Как карта откликается на твой запрос?",
    "10. Какое главное осознание у тебя сейчас?"
]

FINAL_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Да")],
        [KeyboardButton(text="🤔 Частично")],
        [KeyboardButton(text="❌ Нет")]
    ],
    resize_keyboard=True
)


# ================= FSM =================
class Session(StatesGroup):
    request = State()
    question = State()
    final = State()


# ================= BOT =================
bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# ================= HANDLERS =================
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
 await message.answer(
    "Привет 👋\n\n"
    "Этот бот поможет тебе исследовать свой запрос с помощью MAC-карт.\n\n"
    "✍️ Напиши свой запрос одним сообщением, и для тебя выйдет случайная карта."
)
    await state.set_state(Session.request)


@dp.message(Session.request, F.text)
async def handle_request(message: Message, state: FSMContext):
    if not os.path.exists(CARDS_FOLDER):
        await message.answer("❌ Папка с картами не найдена на сервере.")
        return

    cards = [
        f for f in os.listdir(CARDS_FOLDER)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not cards:
        await message.answer("❌ В папке cards нет изображений.")
        return

    card = random.choice(cards)
    photo_path = os.path.join(CARDS_FOLDER, card)

    await state.update_data(
        user_request=message.text,
        card=card,
        answers=[],
        question_index=0
    )

    await message.answer_photo(
        photo=FSInputFile(photo_path),
        caption="Посмотри на карту 20–30 секунд.\n"
        "Опиши подробно: что ты видишь (детали, цвета, образы) и какие чувства это вызывает.\n"
        "Пиши как можно конкретнее."
    )

    await message.answer(QUESTIONS[0])
    await state.set_state(Session.question)


@dp.message(Session.question, F.text)
async def handle_questions(message: Message, state: FSMContext):
    data = await state.get_data()

    answers = data["answers"]
    index = data["question_index"]

    answers.append(message.text)
    index += 1

    await state.update_data(answers=answers, question_index=index)

    if index < len(QUESTIONS):
        await message.answer(QUESTIONS[index])
    else:
        await message.answer(
            "Удалось ли тебе найти ответ или направление для своего запроса?",
            reply_markup=FINAL_KEYBOARD
        )
        await state.set_state(Session.final)


@dp.message(Session.final, F.text.in_(["✅ Да", "🤔 Частично", "❌ Нет"]))
async def handle_final(message: Message, state: FSMContext):
    data = await state.get_data()

    report = (
        "🧠 НОВАЯ MAC-СЕССИЯ\n\n"
        f"👤 Клиент: @{message.from_user.username or 'без username'}\n\n"
        f"📌 Запрос:\n{data['user_request']}\n\n"
        f"🃏 Карта: {data['card']}\n\n"
        "✍️ Ответы:\n"
    )

    for q, a in zip(QUESTIONS, data["answers"]):
        report += f"\n{q}\n— {a}\n"

    report += f"\n🔚 Финальный ответ клиента: {message.text}"

    await bot.send_message(ADMIN_CHAT_ID, report)
    await message.answer(CONTACT_TEXT, reply_markup=ReplyKeyboardRemove())
    await state.clear()


# ================= RUN =================
async def main():
    logging.info("🤖 Bot polling started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



