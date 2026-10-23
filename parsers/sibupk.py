import re

from parsers.base import Step, UniversityParser, post_form, select_options, table_to_text

URL = "http://old.sibupk.su/services/shedule_new/index.php?mode=1"

DAYS = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота")

# enter после каждого дня недели
def format_days(text: str) -> str:
    pattern = "|".join(DAYS)
    return re.sub(rf"(?<!\n\n)(?=(?:{pattern})\b)", "\n\n", text).lstrip()

# шаблон полей для data в post
FIELDS = {
    "forma": "id_Forma",
    "fak": "id_Fak",
    "kurs": "Kurs",
    "group": "NamePodGrup",
    "date_range": "RangeNedel",
}

# Парсер для СИБУПК
class SibupkParser(UniversityParser):
    name = "СИБУПК" # имя парсера
    steps = [ # шаги парсера
        Step("forma", "Выберите форму обучения", {
            "Очная": "1", "Заочная": "2", "Очно-заочная": "4",
        }),
        Step("fak", "Выберите факультет", {
            "Отдел магистратуры и аспирантуры": "11",
            "Торгово-технологический факультет": "1",
            "Факультет экономики и управления": "3",
            "Юридический факультет": "5",
        }),
        Step("kurs", "Выберите курс", {f"Курс {i}": str(i) for i in range(1, 6)}),
        Step("group", "Выберите группу"),
        Step("date_range", "Выберите период"),
    ]

    # Формирование данных для отправки в data
    def _data(self, params: dict, *keys: str) -> dict:
        return {FIELDS[k]: params[k] for k in keys}

    # Загрузка данных для выбора группы и периода
    async def _load(self, params: dict, select: str, *keys: str) -> dict[str, str]:
        return select_options(await post_form(URL, self._data(params, *keys)), select)

    # возвращает кнопки для текущего шага
    async def get_step_choices(self, step: Step, params: dict) -> dict[str, str]:
        if step.key == "group":
            return await self._load(params, "NamePodGrup", "forma", "fak", "kurs")
        if step.key == "date_range":
            return await self._load(params, "RangeNedel", "forma", "fak", "kurs", "group")
        return step.choices

    # парсинг расписания
    async def parse(self, params: dict) -> str:
        html = await post_form(URL, self._data(params, *FIELDS))
        return format_days(table_to_text(html))