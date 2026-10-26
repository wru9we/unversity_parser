from aiogram import Router, F
from aiogram.filters import Command, or_f
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup

from parsers import PARSERS

router = Router()
user_state: dict = {} # состояние пользователя

PAGE_SIZE = 8
BTN_NEXT = "Вперёд »"
BTN_PREV = "« Назад"
BTN_HOME = "К выбору вуза"

# Создание клавиатуры для бота
def keyboard(*labels: str, nav: list[str] | None = None) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t)] for t in labels]
    if nav:
        rows.append([KeyboardButton(text=t) for t in nav])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def page_choices(all_choices: dict, page: int) -> dict:
    items = list(all_choices.items())
    start = page * PAGE_SIZE
    return dict(items[start : start + PAGE_SIZE])
def nav_buttons(all_choices: dict, page: int) -> list[str]:
    nav = []
    if page > 0:
        nav.append(BTN_PREV)
    if (page + 1) * PAGE_SIZE < len(all_choices):
        nav.append(BTN_NEXT)
    nav.append(BTN_HOME)
    return nav

# Запрос выбора вуза из клавиатуры
async def ask_university(message: Message) -> None:
    user_state[message.from_user.id] = {}
    await message.answer("Выберите ВУЗ", reply_markup=keyboard(*PARSERS))

async def render_step(message: Message, state: dict) -> None:
    parser = PARSERS[state["university"]]
    step = parser.steps[state["step_i"]]
    all_choices = state["all_choices"]
    page = state.get("page", 0)
    visible = page_choices(all_choices, page)
    state["choices"] = all_choices  # поиск по полному списку
    total_pages = max(1, (len(all_choices) + PAGE_SIZE - 1) // PAGE_SIZE)
    prompt = step.prompt
    if total_pages > 1:
        prompt = f"{step.prompt}\n(стр. {page + 1}/{total_pages})"
    await message.answer(
        prompt,
        reply_markup=keyboard(*visible, nav=nav_buttons(all_choices, page)),
    )

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

    state["all_choices"] = choices
    state["page"] = 0
    await render_step(message, state)

# Обработка команды /start или Назад -> запрос выбора вуза
@router.message(or_f(Command("start"), F.text == BTN_HOME))
async def start(message: Message):
    await ask_university(message)

# Выбор вуза, вызывается после выбора вуза из клавиатуры
@router.message(F.text.in_(PARSERS))
async def choose_university(message: Message):
    state = {"university": message.text, "params": {}, "step_i": 0, "page": 0}
    user_state[message.from_user.id] = state
    await show_step(message, state)


@router.message(F.text)
async def wizard_step(message: Message):
    state = user_state.get(message.from_user.id)
    if not state or "university" not in state:
        await ask_university(message)
        return

    # пагинация
    if message.text == BTN_NEXT:
        all_choices = state.get("all_choices") or {}
        max_page = max(0, (len(all_choices) - 1) // PAGE_SIZE)
        state["page"] = min(state.get("page", 0) + 1, max_page)
        await render_step(message, state)
        return
    if message.text == BTN_PREV:
        state["page"] = max(0, state.get("page", 0) - 1)
        await render_step(message, state)
        return


    parser = PARSERS[state["university"]]
    step = parser.steps[state["step_i"]]
    choices = state.get("choices") or state["all_choices"] or step.choices

    if message.text not in choices:
        await render_step(message, state)
        return

    state["params"][step.key] = choices[message.text]
    state["step_i"] += 1
    state["page"] = 0

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