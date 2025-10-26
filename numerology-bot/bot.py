import datetime
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio 



PROMO_FILE = "numerology-bot/promocodes.json"
PROMO_USED_FILE = "numerology-bot/promo_used.json"

def load_promocodes():
    try:
        with open(PROMO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def load_promo_used():
    try:
        with open(PROMO_USED_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except FileNotFoundError:
        return {}

def save_promo_used(data):
    with open(PROMO_USED_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_user_access():
    try:
        with open(USER_ACCESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_access(data):
    with open(USER_ACCESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def save_paid_access(user_id, until_str):
    user_access = load_user_access()
    user_data = user_access.get(user_id, {})
    user_data["until"] = until_str
    user_access[user_id] = user_data
    save_user_access(user_access)


def has_paid_access(user_id: int):
    user_access = load_user_access()
    user_data = user_access.get(str(user_id), {})
    until = user_data.get("until")
    if until:
        return datetime.datetime.now() < datetime.datetime.strptime(until, "%Y-%m-%d %H:%M:%S")
    return False

BOT_TOKEN = 'ТОКЕН'
#BOT_TOKEN = 'ТОКЕН'
ADMIN_ID = 1079521408
bot = Bot(token=BOT_TOKEN)
router = Router()
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)

main_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🔮 Узнать число", callback_data="free_reading"),
            InlineKeyboardButton(text="✨ Тайны судьбы", callback_data="DiveDeeper"),
        ],
        [
            InlineKeyboardButton(text="🤖 Канал бота", callback_data="Channel"),
            InlineKeyboardButton(text="🎁 Промокоды", callback_data="Promocode"),
        ],
        [
            #InlineKeyboardButton(text="⭐ Заказать бота — тут", callback_data="OrderAbot")
        ],
    ]
)

paid_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✨ Тайны судьбы", callback_data="DiveDeeper")
        ],
        [
            InlineKeyboardButton(text="🎁 Промокоды", callback_data="Promocode")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="BackButton")
        ],
    ]
)

cancle_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="BackButton")
        ],
    ]
)

pay_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Купить", callback_data="Paybutton"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="BackButton"),
        ],
    ]
)

paying_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Я оплатил/а", callback_data="MyPay"),
            InlineKeyboardButton(text="⬅️ Отмена", callback_data="BackButton"),
        ]
    ]
)

admin_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Редактировать промокоды", callback_data="EditPromocodes")
        ]
    ]
)

file_path = Path(__file__).parent / "Photos" / "HelenaPhoyo.png"

class EditPromoStates(StatesGroup):
    waiting_for_action = State()
    waiting_for_code = State()
    waiting_for_time = State()
    waiting_for_delete = State()

@router.callback_query(F.data == "EditPromocodes")
async def edit_promocodes_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.")
        return
    await callback.message.answer(
        "Что сделать с промокодами?\n"
        "1. Добавить — напиши: добавить\n"
        "2. Удалить — напиши: удалить\n"
        "3. Изменить срок — напиши: изменить",
        reply_markup=cancle_kb
    )
    await state.set_state(EditPromoStates.waiting_for_action)

@router.message(EditPromoStates.waiting_for_action)
async def promo_action(message: types.Message, state: FSMContext):
    action = message.text.lower()
    if action == "добавить":
        await message.answer("Введи промокод (только латиница и цифры):")
        await state.set_state(EditPromoStates.waiting_for_code)
        await state.update_data(action="add")
    elif action == "удалить":
        await message.answer("Введи промокод, который удалить:")
        await state.set_state(EditPromoStates.waiting_for_delete)
    elif action == "изменить":
        await message.answer("Введи промокод, срок которого изменить:")
        await state.set_state(EditPromoStates.waiting_for_code)
        await state.update_data(action="edit")
    else:
        await message.answer("Не понял. Напиши: добавить, удалить или изменить.")

@router.message(EditPromoStates.waiting_for_code)
async def promo_code_input(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    data = await state.get_data()
    action = data.get("action")
    promocodes = load_promocodes()
    if action == "add":
        if code in promocodes:
            await message.answer("Такой промокод уже есть.")
            await state.clear()
            return
        await state.update_data(code=code)
        await message.answer("Введи срок: например, minutes=60, hours=2, days=1")
        await state.set_state(EditPromoStates.waiting_for_time)
    elif action == "edit":
        if code not in promocodes:
            await message.answer("Такого промокода нет.")
            await state.clear()
            return
        await state.update_data(code=code)
        await message.answer("Введи новый срок: например, minutes=60, hours=2, days=1")
        await state.set_state(EditPromoStates.waiting_for_time)

@router.message(EditPromoStates.waiting_for_time)
async def promo_time_input(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    data = await state.get_data()
    code = data.get("code")
    action = data.get("action")
    promocodes = load_promocodes()
    try:
        # Пример: minutes=60, hours=2, days=1
        time_dict = {}
        for part in time_str.split(","):
            k, v = part.strip().split("=")
            time_dict[k.strip()] = int(v.strip())
        promocodes[code] = time_dict
        with open(PROMO_FILE, "w", encoding="utf-8") as f:
            json.dump(promocodes, f, ensure_ascii=False, indent=4)
        await message.answer(f"Промокод {code} успешно {'добавлен' if action=='add' else 'обновлён'}!")
    except Exception as e:
        await message.answer("Ошибка формата. Пример: minutes=60, hours=2, days=1")
    await state.clear()

@router.message(EditPromoStates.waiting_for_delete)
async def promo_delete_input(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    promocodes = load_promocodes()
    if code in promocodes:
        promocodes.pop(code)
        with open(PROMO_FILE, "w", encoding="utf-8") as f:
            json.dump(promocodes, f, ensure_ascii=False, indent=4)
        await message.answer(f"Промокод {code} удалён.")
    else:
        await message.answer("Такого промокода нет.")
    await state.clear()


class PromoStates(StatesGroup):
    waiting_for_promocode = State()

@router.callback_query(F.data == "Promocode")
async def promocode_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите ваш промокод:",
        reply_markup=cancle_kb
    )
    await state.set_state(PromoStates.waiting_for_promocode)

@router.message(PromoStates.waiting_for_promocode)
async def process_promocode(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    user_id = str(message.from_user.id)
    promocodes = load_promocodes()
    user_access = load_user_access()
    promo_used = load_promo_used()

    # Проверка: если пользователь уже использовал этот промокод
    if user_id in promo_used and promo_used[user_id]["promocode"] == code:
        await message.answer("❗ Ты уже использовал этот промокод. Введи другой.")
        await state.set_state(PromoStates.waiting_for_promocode)
        return

    if code in promocodes:
        promo = promocodes[code]
        now = datetime.datetime.now()
        if "minutes" in promo:
            until = now + datetime.timedelta(minutes=promo["minutes"])
            period = f"{promo['minutes']} минут"
        elif "hours" in promo:
            until = now + datetime.timedelta(hours=promo["hours"])
            period = f"{promo['hours']} часов"
        elif "days" in promo:
            until = now + datetime.timedelta(days=promo["days"])
            period = f"{promo['days']} дней"
        else:
            until = now + datetime.timedelta(days=1)
            period = "1 день"
        until_str = until.strftime("%Y-%m-%d %H:%M:%S")
        user_access[user_id] = {"until": until_str, "trial_used": False}
        save_user_access(user_access)
        promo_used[user_id] = {"promocode": code, "until": until_str}
        save_promo_used(promo_used)
        await message.answer(
            f"✅ Промокод активирован!\n"
            f"Доступ к платной версии открыт на {period}.",
            reply_markup=main_kb
        )
        await state.clear()
    else:
        await message.answer("❌ Промокод неверный. Попробуйте ещё раз.")
        await state.set_state(PromoStates.waiting_for_promocode)

#{"7734461744": {"until": "2025-09-19 21:03:57", "trial_used": false}}
class BirthDateStates(StatesGroup):
    waiting_for_date = State()
    confirm_date = State()


@router.callback_query(F.data == "DiveDeeper")
async def divedeeper_callback(callback: CallbackQuery, state: FSMContext):
    
    await callback.message.answer(
        "✨ Погрузись глубже ✨\n"
        "Открой для себя полный разбор судьбы, любви и твоего пути.\n"
        "Это платная версия — всего 490₽.\n"
        "💳 Оплата доступна через ЮKassa.\n",
        reply_markup=pay_kb
         
    )


@router.callback_query(F.data == "Paybutton")
async def Paybutton_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Реквизиты для перевода:\n\n"
        "💰 Валюта: Российский рубль (RUB)\n"
        "👤 Получатель: ТРУХИНА ЕЛЕНА АНАТОЛЬЕВНА\n"
        "🏦 Банк: СЕВЕРО-ЗАПАДНЫЙ БАНК ПАО СБЕРБАНК\n"
        "💳 Счёт получателя: 40817810855005812487\n"
        "🔑 БИК: 044030653\n"
        "🔗 Корр. счёт: 30101810500000000653\n"
        "🌍 SWIFT: SABRRU2P\n"
        "📍 Адрес банка: 191124, Санкт-Петербург, ул. Красного Текстильщика, 2\n"
        #Тут ставишь ссылку а именно в месте href="ссылка"
        '👉 Для удобства вы можете оплатить онлайн через ЮKassa по ссылке: <a href="https://yookassa.ru/my/i/aMO7t9swyznP/l">Страничка оплаты</a>\n\n\n',
    parse_mode="HTML",
        reply_markup=paying_kb
    )



# --- Обработка кнопки MyPay ---
@dp.callback_query(F.data == "MyPay")
async def ask_payment_proof(callback: types.CallbackQuery):
    await callback.message.answer(
        "👉 Отправь, пожалуйста, скриншот чека оплаты сюда в чат 📸"
    )


# --- Приём скрина ---
@dp.message(F.photo)
async def handle_payment_proof(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or "без username"

    caption = (
        f"📥 Новый скрин оплаты!\n\n"
        f"👤 Пользователь: @{username}\n"
        f"🆔 ID: {user_id}\n\n"
        "Подтвердить оплату?"
    )

    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить платёж", callback_data=f"confirm:{user_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Отклонить платёж", callback_data=f"decline:{user_id}")
        ]
    ])

    # пересылаем админу
    photo_id = msg.photo[-1].file_id
    await bot.send_photo(
        ADMIN_ID,
        photo=photo_id,
        caption=caption,
        reply_markup=confirm_kb
    )

    await msg.answer("📩 Скрин отправлен на проверку админу. Ожидай подтверждения 🙏")

@dp.callback_query(F.data.startswith("decline:"))
async def decline_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    await bot.send_message(
        user_id,
        "❌ К сожалению, оплата не прошла или была отклонена администратором.\n"
        "Попробуйте ещё раз или обратитесь в поддержку."
    )

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n❌ Оплата отклонена!",
        reply_markup=None
    )


# --- Подтверждение оплаты админом ---
@dp.callback_query(F.data.startswith("confirm:"))
async def confirm_payment(callback: types.CallbackQuery):
    user_id = int(callback.data.split(":")[1])

    user_access = load_user_access()

    # Всегда храним user_id как строку!
    user_id_str = str(user_id)

    # Делаем оплату хотя бы на 30 дней (или сколько хочешь)
    until = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

    # Сохраняем доступ
    user_access[user_id_str] = {
        "until": until,
        "trial_used": False
    }
    save_user_access(user_access)

    await bot.send_message(
        user_id,
        "✅ Ваш платёж подтверждён!\n\n"
        "✨ Доступ к платной версии открыт.\n"
        "Добро пожаловать в мир чисел 🔮",
        reply_markup=main_kb
    )

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n✅ Оплата подтверждена!",
        reply_markup=None
    )



@router.callback_query(F.data == "BackButton")
async def back_callback(callback: CallbackQuery, state: FSMContext):
    photo = FSInputFile(file_path)
    await callback.message.answer_photo(
        photo=photo,
        caption=(
            "Приветствую тебя, мудрый странник! ✨\n\n"
            "Я — Хелена, проводница в мир чисел и скрытых смыслов. Каждая цифра хранит в себе тайный узор\n"
            "судьбы, и я помогу тебе услышать этот шёпот Вселенной.\n\n"
            "♦ Хочешь узнать, какие откровения числа приготовили именно для тебя?\n\n"
            "♦ Сделай первый шаг — выбери свой путь, и тайна начнёт открываться… 🌙🔮\n\n"
            "🌟 Раскрой число судьбы — бесплатный мини-разбор откроет первую тайну\n"
            "✨ Погрузись глубже — полный разбор судьбы, любви и твоего пути. Стоимость 490₽\n"
            "🌟 У тебя есть промокод и ты хочешь получить свой разбор.\n"
            "Что выберешь, мой друг?\n\n"
        ),
        reply_markup=main_kb
    )


@router.callback_query(F.data == "Channel")
async def channel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "🌌 Мой искатель, мы заглянули в самые глубины твоей судьбы.\n\n"
        "Числа оживают и открывают новые смыслы."
        "Следуй за звёздным светом в канале @helenatruth,\n"
        "чтобы раскрывать тайны и находить ответы для своей души.\n",
        reply_markup=cancle_kb
    )
    

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Добро пожаловать, админ!",
            reply_markup=admin_kb
        )
    else:
        photo = FSInputFile(file_path)
        await message.answer_photo(
            photo=photo,
            caption=(
                "Приветствую тебя, мудрый странник! ✨\n\n"
                "Я — Хелена, проводница в мир чисел и скрытых смыслов. Каждая цифра хранит в себе тайный узор\n"
                "судьбы, и я помогу тебе услышать этот шёпот Вселенной.\n\n"
                "♦ Хочешь узнать, какие откровения числа приготовили именно для тебя?\n\n"
                "♦ Сделай первый шаг — выбери свой путь, и тайна начнёт открываться… 🌙🔮\n\n"
                "🌟 Раскрой число судьбы — бесплатный мини-разбор откроет первую тайну\n"
                "✨ Погрузись глубже — полный разбор судьбы, любви и твоего пути. Стоимость 490₽\n"
                "🌟 У тебя есть промокод и ты хочешь получить свой разбор.\n"
                "Что выберешь, мой друг?\n\n"
            ),
            reply_markup=main_kb
        )

@router.callback_query(F.data == "free_reading")
async def free_reading_callback(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    user_access = load_user_access()

    if has_paid_access(user_id):
        # Платный доступ — сразу даём доступ к расчету
        await callback.message.answer(
            "✨ У тебя открыт платный доступ! Введи дату рождения для расчёта числа судьбы.",
            reply_markup=cancle_kb
        )
        await state.set_state(BirthDateStates.waiting_for_date)
        await callback.answer()
        return

    elif user_access.get(user_id, {}).get("trial_used", False):
        # Бесплатный мини-разбор уже использован
        await callback.message.answer(
            "🔒 Бесплатный мини-разбор уже использован.\n"
            "Чтобы узнать число судьбы, активируй платную версию или введи промокод.",
            reply_markup=paid_kb
        )
        await callback.answer()
        return

    else:
        # Бесплатный мини-разбор доступен
        await callback.message.answer(
            "🔢 Числа раскрывают тайны судьбы, мой дорогой искатель.\n\n"
            "Давай начнём с бесплатного мини-разбора твоей даты рождения.\n"
            "📅 Введи её в формате ДД.ММ.ГГГГ, и я открою твоё число судьбы! ✨\n",
            reply_markup=cancle_kb
        )
        await state.set_state(BirthDateStates.waiting_for_date)
        await callback.answer()
    

@router.message(BirthDateStates.waiting_for_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    date_text = message.text
    try:
       
        day, month, year = map(int, date_text.split("."))
        if not (1 <= day <= 31 and 1 <= month <= 12 and year > 0):
            raise ValueError
    except:
        await message.answer("Неверный формат! Пожалуйста, введи дату в формате ДД.ММ.ГГГГ.")
        return

    
    await state.update_data(birth_date=date_text)
    await state.set_state(BirthDateStates.confirm_date)
    await message.answer(f"Твоя дата рождения {date_text}, верно? (да/нет)")


def calc_destiny_number(date_text: str) -> str:
    digits = [int(ch) for ch in date_text if ch.isdigit()]
    total = sum(digits)
    if total in (11, 22, 33):
        return str(total)
    while total > 9:
        total = sum(int(d) for d in str(total))
        if total in (11, 22, 33):
            return str(total)
    return str(total)

USER_ACCESS_FILE = "numerology-bot/user_access.json"

@router.message(BirthDateStates.confirm_date)
async def confirm_date(message: types.Message, state: FSMContext):
    if message.text.lower() in ["да", "yes", "y"]:
        data = await state.get_data()
        birth_date = data.get("birth_date")
        user_id = str(message.from_user.id)
        user_access = load_user_access()

        if has_paid_access(user_id):
            destiny = calc_destiny_number(birth_date)
            await message.answer(
                f"Ваше число судьбы для даты {birth_date}: <b>{destiny}</b>",
                parse_mode="HTML",
                reply_markup=main_kb
            )
            # Отправка PDF только для платного доступа
            pdf_map = {
                "1": "OnePay.pdf",
                "2": "TwoPay.pdf",
                "3": "ThreePay.pdf",
                "4": "FourPay.pdf",
                "5": "FivePay.pdf",
                "6": "SixPay.pdf",
                "7": "SevenPay.pdf",
                "8": "EightPay.pdf",
                "9": "NinePay.pdf",
                "11": "ElevenPay.pdf",
                "22": "TwentyTwoPay.pdf",
                "33": "ThirtyThreePay.pdf"
            }
            pdf_file = pdf_map.get(destiny)
            if pdf_file:
                pdf_path = f"PDFpay/{pdf_file}"
                await message.answer_document(FSInputFile(pdf_path), caption=f"📄 Подробный разбор для числа судьбы {destiny}")
        else:
            # Бесплатный мини-разбор
            trial_used = user_access.get(user_id, {}).get("trial_used", False)
            if not trial_used:
                destiny = calc_destiny_number(birth_date)
                await message.answer(
                    f"Ваше число судьбы для даты {birth_date}: <b>{destiny}</b>\n",
                    parse_mode="HTML",
                    reply_markup=paid_kb
                )
                # Отправка PDF из PDFfile для бесплатной версии
                pdf_map = {
                    "1": "One.pdf",
                    "2": "Two.pdf",
                    "3": "Three.pdf",
                    "4": "Four.pdf",
                    "5": "Five.pdf",
                    "6": "Six.pdf",
                    "7": "Seven.pdf",
                    "8": "Eight.pdf",
                    "9": "Nine.pdf",
                    "11": "Eleven.pdf",
                    "22": "TwentyTwo.pdf",
                    "33": "ThirtyThree.pdf"
                }
                pdf_file = pdf_map.get(destiny)
                if pdf_file:
                    pdf_path = f"PDFfile/{pdf_file}"
                    await message.answer_document(FSInputFile(pdf_path), caption=f"📄 Мини-разбор для числа судьбы {destiny}")
                user_access[user_id] = user_access.get(user_id, {})
                user_access[user_id]["trial_used"] = True
                save_user_access(user_access)
                await state.clear()
            else:
                await message.answer(
                    f"Ваше число судьбы для даты {birth_date} раскрыто! 🌟\n"
                    "Хочешь узнать больше? \n\nПогрузись в полный разбор!",
                    reply_markup=paid_kb
                )
                await state.clear()
    else:
        await state.set_state(BirthDateStates.waiting_for_date)
        await message.answer("Хорошо, введи дату заново в формате ДД.ММ.ГГГГ.")
        


async def main():
    print("Бот Запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
