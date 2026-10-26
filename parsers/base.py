from dataclasses import dataclass, field

import aiohttp
from bs4 import BeautifulSoup

#Шаг выбора в боте, после создания нельзя менять frozen=True
@dataclass(frozen=True)
class Step:
    key: str # куда сохранить ответ в params
    prompt: str # текст сообщения пользователю step
    choices: dict[str, str] = field(default_factory=dict) # кнопки {подпись: значение}; по умолчанию {}

# Базовый класс для парсеров вузов
class UniversityParser:
    name: str
    steps: list[Step]

    # Получение вариантов для шага
    async def get_step_choices(self, step: Step, params: dict) -> dict[str, str]:
        return step.choices

async def get_html(url: str, timeout=20) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout,
        ) as response:
            return await response.text()


# Отправка POST-запроса на url с данными
async def post_form(url: str, data: dict, timeout=20) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, 
            data=data, 
            headers={"User-Agent": "Mozilla/5.0"}, 
            timeout=timeout
        ) as response:
            # Возвращаем HTML ответа
            return await response.text()


# Преобразование HTML таблицы в текст
def table_to_text(html: str) -> str:
    tables = BeautifulSoup(html, "html.parser").find_all("table")
    if not tables:
        return "Расписание не найдено"
    rows = [
        " | ".join(td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"]))
        for tr in tables[-1].find_all("tr")
    ]
    rows = [r for r in rows if r.strip()]
    return "\n".join(rows) if rows else "Расписание не найдено"


# Преобразование HTML в кнопки для бота
def select_options(html: str, name: str) -> dict[str, str]:
    select = BeautifulSoup(html, "html.parser").find("select", {"name": name})
    if not select:
        return {}
    choices = {}
    for opt in select.find_all("option"):
        value = (opt.get("value") or "").strip()
        label = opt.get_text(" ", strip=True)
        if value and label and set(label) - {"-", " "}:
            choices[label] = value
    return choices