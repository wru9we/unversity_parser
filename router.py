from aiogram import Router, F
from aiogram.filters import Command, or_f
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

from parsers import PARSERS

router = Router()
user_state: dict = {} # состояние пользователя

# Создание клавиатуры для бота
def keyboard(*labels: str, back=False) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t)] for t in labels]
    if back:
        rows.append([KeyboardButton(text="Назад")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# Запрос выбора вуза из клавиатуры
async def ask_university(message: Message) -> None:
    user_state[message.from_user.id] = {}
    await message.answer("Выберите ВУЗ", reply_markup=keyboard(*PARSERS))

# Показывает текущий шаг выбора
async def show_step(message: Message, state: dict) -> None:
    parser = PARSERS[state["university"]]
    step = parser.steps[state["step_i"]]
    try:
        choices = await parser.get_step_choices(step, state["params"])
    except Exception as e:
        await message.answer(f"Не удалось загрузить варианты:\n{e}")
        await ask_university(message)
        return
    if not choices:
        await message.answer("Нет доступных вариантов.")
        await ask_university(message)
        return
    state["choices"] = choices
    await message.answer(step.prompt, reply_markup=keyboard(*choices, back=True))

# Обработка команды /start или Назад -> запрос выбора вуза
@router.message(or_f(Command("start"), F.text == "Назад"))
async def start(message: Message):
    await ask_university(message)

# Выбор вуза, вызывается после выбора вуза из клавиатуры
@router.message(F.text.in_(PARSERS))
async def choose_university(message: Message):
    state = {"university": message.text, "params": {}, "step_i": 0}
    user_state[message.from_user.id] = state
    await show_step(message, state)


@router.message(F.text)
async def wizard_step(message: Message):
    state = user_state.get(message.from_user.id)


    parser = PARSERS[state["university"]]
    step = parser.steps[state["step_i"]]
    choices = state.get("choices") or step.choices

    if message.text not in choices:
        await message.answer(step.prompt, reply_markup=keyboard(*choices, back=True))
        return

    state["params"][step.key] = choices[message.text]
    state["step_i"] += 1

    if state["step_i"] < len(parser.steps):
        await show_step(message, state)
        return

    try:
        text = await parser.parse(state["params"])
        for i in range(0, len(text), 4000):
            await message.answer(text[i : i + 4000])
    except Exception as e:
        await message.answer(f"Ошибка:\n{e}")

    await message.answer("Хотите посмотреть другое расписание?")
    await ask_university(message)