import asyncio
import random
import os



from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext


# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_CHAT_ID = 6567991779
CARDS_FOLDER = "cards"

CONTACT_TEXT = (
    "✨ Если хочешь глубже разобрать свой запрос,\n"
    "Анжела проводит индивидуальные MAC-сессии.\n\n"
    "👤 Анжела Цой\n"
    "📞 +996 551 040 832\n"
    "📸 Instagram: @anjela_tsoy_psy"
)

QUESTIONS = [
    "Что ты первым заметил(а) на карте?",
    "Какие эмоции вызывает эта карта?",
    "Есть ли на карте персонаж? Кто он для тебя?",
    "Что на карте похоже на твою ситуацию?",
    "Что на карте тебе не нравится или напрягает?",
    "Где на карте ты, если представить себя внутри?",
    "Чего не хватает на карте?",
    "Что бы ты хотел(а) изменить на карте?",
    "Как карта откликается на твой запрос?",
    "Какое главное осознание у тебя сейчас?"
]

FINAL_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="final_yes")],
        [InlineKeyboardButton(text="🤔 Частично", callback_data="final_partial")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="final_no")]
    ]
)


# ================== FSM ==================
class Session(StatesGroup):
    request = State()
    question = State()
    final = State()


# ================== BOT ==================
bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# ================== START ==================
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет 👋\n\n"
        "Этот бот поможет тебе исследовать свой запрос с помощью MAC-карт.\n\n"
        "✍️ Напиши свой запрос одним сообщением. \n\n" 
        "После этого для тебя автоматически выйдет случайная карта."
    )
    await state.set_state(Session.request)


# ================== REQUEST ==================
@dp.message(Session.request)
async def handle_request(message: Message, state: FSMContext):
    await state.update_data(
        user_request=message.text,
        answers=[],
        question_index=0,
        username=message.from_user.username,
        user_id=message.from_user.id
    )

    cards = [
        f for f in os.listdir(CARDS_FOLDER)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    card = random.choice(cards)
    await state.update_data(card=card)

    await message.answer_photo(
        FSInputFile(os.path.join(CARDS_FOLDER, card)),
        caption="Посмотри на карту.\nОпиши, что ты видишь и что чувствуешь."
    )

    await message.answer(f"1. {QUESTIONS[0]}")
    await state.set_state(Session.question)


# ================== QUESTIONS ==================
@dp.message(Session.question)
async def handle_questions(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data["answers"]
    index = data["question_index"]

    answers.append(message.text)
    index += 1

    await state.update_data(answers=answers, question_index=index)

    if index < len(QUESTIONS):
        await message.answer(f"{index+1}. {QUESTIONS[index]}")
    else:
        await state.set_state(Session.final)
        await message.answer(
            "Удалось ли тебе найти ответ или направление для своего запроса?",
            reply_markup=FINAL_KEYBOARD
        )


# ================== FINAL ==================
@dp.callback_query(F.data.startswith("final_"))
async def handle_final(call: CallbackQuery, state: FSMContext):
    await call.answer("Спасибо 🙏")

    data = await state.get_data()

    final_map = {
        "final_yes": "Да",
        "final_partial": "Частично",
        "final_no": "Нет"
    }
    final_answer = final_map.get(call.data, call.data)

    username = f"@{data['username']}" if data["username"] else "не указан"
    user_info = f"{username} (ID: {data['user_id']})"

    # 1️⃣ отправляем КАРТУ Анжеле
    try:
        await bot.send_photo(
            ADMIN_CHAT_ID,
            FSInputFile(os.path.join(CARDS_FOLDER, data["card"])),
            caption=f"🃏 Карта: {data['card']}"
        )
    except Exception as e:
        print("Ошибка отправки карты:", e)

    # 2️⃣ формируем текст с вопросами и ответами
    text = (
        "🧠 НОВАЯ MAC-СЕССИЯ\n\n"
        f"👤 Клиент:\n{user_info}\n\n"
        f"📝 Запрос:\n{data['user_request']}\n\n"
        "Вопросы и ответы:\n\n"
    )

    for i, (q, a) in enumerate(zip(QUESTIONS, data["answers"]), 1):
        text += f"{i}. {q}\n— {a}\n\n"

    text += f"🔚 Финальный ответ:\n{final_answer}"

    await bot.send_message(ADMIN_CHAT_ID, text)

    # клиенту — контакты
    await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(CONTACT_TEXT)

    await state.clear()


# ================== RUN ==================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



