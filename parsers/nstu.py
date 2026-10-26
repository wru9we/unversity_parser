from urllib.parse import quote

from bs4 import BeautifulSoup

from parsers.base import Step, UniversityParser, get_html

INDEX_URL = "https://www.nstu.ru/studies/schedule/schedule_classes"
SCHEDULE_URL = "https://www.nstu.ru/studies/schedule/schedule_classes/schedule"

DAYS = {
    "пн": "Понедельник",
    "вт": "Вторник",
    "ср": "Среда",
    "чт": "Четверг",
    "пт": "Пятница",
    "сб": "Суббота",
    "вс": "Воскресенье",
}


def _faculty_blocks(soup: BeautifulSoup):
    return [
        f for f in soup.select(".schedule__faculty")
        if f.select_one(".schedule__faculty-title")
    ]


def _faculty_by_name(soup: BeautifulSoup, name: str):
    for fac in _faculty_blocks(soup):
        title = fac.select_one(".schedule__faculty-title").get_text(strip=True)
        if title == name:
            return fac
    return None


def _form_label(type_el) -> str:
    title_el = type_el.select_one(".schedule__faculty-type__title")
    sub_el = type_el.select_one(".schedule__faculty-type__subtitle")
    title = title_el.get_text(strip=True) if title_el else ""
    sub = sub_el.get_text(strip=True) if sub_el else ""
    if title and sub:
        return f"{title} · {sub}"
    return title or sub


def _type_by_label(fac, label: str):
    for type_el in fac.select(".schedule__faculty-type"):
        if _form_label(type_el) == label:
            return type_el
    return None


def _course_by_title(type_el, title: str):
    for course in type_el.select(".schedule__faculty-course"):
        t = course.select_one(".schedule__faculty-course__title")
        if t and t.get_text(strip=True) == title:
            return course
    return None


def _ready_groups(course) -> dict[str, str]:
    choices = {}
    for a in course.select("a.schedule__faculty-groups__item"):
        classes = a.get("class") or []
        if "schedule__faculty-groups__item-notready" in classes:
            continue
        name = a.get_text(strip=True)
        if name:
            choices[name] = name
    return choices


def _lesson_text(item) -> str:
    # "Линейная алгебра · Павлюк И. И. | Лекция"
    parts = []
    for child in item.children:
        if getattr(child, "name", None) in (None, "a"):
            text = child.get_text(" ", strip=True) if hasattr(child, "get_text") else str(child).strip()
            if text:
                parts.append(text)
    subject = " ".join(parts).strip(" ·")
    typework = item.select_one(".schedule__table-typework")
    tw = typework.get_text(" ", strip=True) if typework else ""
    if subject and tw:
        return f"{subject} | {tw}"
    return subject or tw


def schedule_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".schedule__table-body")
    if not body:
        return "Расписание не найдено"

    lines: list[str] = []
    for day_row in body.find_all("div", class_="schedule__table-row", recursive=False):
        day_el = day_row.select_one(".schedule__table-day")
        if not day_el:
            continue

        day_raw = day_el.get_text(" ", strip=True)  # "пн 26.10"
        day_key = day_raw.split()[0].lower() if day_raw else ""
        day_name = DAYS.get(day_key, day_raw)
        date = ""
        date_el = day_el.select_one(".schedule__table-date")
        if date_el:
            date = date_el.get_text(strip=True)

        header = f"{day_name} {date}".strip()
        day_lines: list[str] = []

        # строки времени внутри дня
        for time_row in day_row.select(":scope > .schedule__table-cell > .schedule__table-row"):
            time_el = time_row.select_one(".schedule__table-time")
            if not time_el:
                continue
            time = time_el.get_text(strip=True)

            items = []
            for item in time_row.select("[data-type=item] .schedule__table-item"):
                text = _lesson_text(item)
                if not text:
                    continue
                room_el = item.find_parent(attrs={"data-type": "item"})
                # аудитория рядом в соседней ячейке
                room = ""
                parent_row = item.find_parent("div", class_="schedule__table-row")
                if parent_row:
                    room_cell = parent_row.select_one('[data-type="class"] .schedule__table-class')
                    if room_cell:
                        room = room_cell.get_text(strip=True)
                if room:
                    items.append(f"{text} | {room}")
                else:
                    items.append(text)

            if not items:
                continue
            day_lines.append(f"{time} | " + " ; ".join(items))

        if day_lines:
            lines.append(header)
            lines.extend(day_lines)
            lines.append("")

    text = "\n".join(lines).strip()
    return text or "Расписание не найдено"


class NstuParser(UniversityParser):
    name = "НГТУ"
    steps = [
        Step("faculty", "Выберите факультет"),
        Step("form", "Выберите форму обучения"),
        Step("course", "Выберите курс"),
        Step("group", "Выберите группу"),
        Step("week", "Выберите неделю"),
    ]

    async def get_step_choices(self, step: Step, params: dict) -> dict[str, str]:
        if step.key == "week":
            html = await get_html(
                f"{SCHEDULE_URL}?group={quote(params['group'])}"
            )
            soup = BeautifulSoup(html, "html.parser")
            choices = {}
            for a in soup.select("a.js-week-item[data-week]"):
                week = a.get("data-week", "").strip()
                if week:
                    choices[f"Неделя {week}"] = week
            return choices

        html = await get_html(INDEX_URL)
        soup = BeautifulSoup(html, "html.parser")

        if step.key == "faculty":
            return {
                f.select_one(".schedule__faculty-title").get_text(strip=True): 
                f.select_one(".schedule__faculty-title").get_text(strip=True)
                for f in _faculty_blocks(soup)
            }

        fac = _faculty_by_name(soup, params["faculty"])
        if not fac:
            return {}

        if step.key == "form":
            return {
                _form_label(t): _form_label(t)
                for t in fac.select(".schedule__faculty-type")
                if _form_label(t)
            }

        type_el = _type_by_label(fac, params["form"])
        if not type_el:
            return {}

        if step.key == "course":
            choices = {}
            for course in type_el.select(".schedule__faculty-course"):
                t = course.select_one(".schedule__faculty-course__title")
                if not t:
                    continue
                title = t.get_text(strip=True)
                # пропускаем курсы без готовых групп
                if _ready_groups(course):
                    choices[title] = title
            return choices

        if step.key == "group":
            course = _course_by_title(type_el, params["course"])
            if not course:
                return {}
            return _ready_groups(course)

        return {}

    async def parse(self, params: dict) -> str:
        url = (
            f"{SCHEDULE_URL}?group={quote(params['group'])}"
            f"&week={params['week']}"
        )
        html = await get_html(url)
        title = f"НГТУ · {params['group']} · неделя {params['week']}\n\n"
        return title + schedule_to_text(html)