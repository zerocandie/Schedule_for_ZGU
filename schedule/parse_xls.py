# Собирает schedule.js из xls в папке «Осень 2026-27 расписание».
# Сессионные xlsx - консультации и экзамены по датам, в недельную таблицу не входят.

import json
import os
import re

import xlrd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOLDER = os.path.join(ROOT, "Осень 2026-27 расписание")
OUT = os.path.join(ROOT, "schedule", "schedule.js")

FILES = [
    ("1-ochnoe.xls", "bachelor", "fulltime"),
    ("2-ochno-zaochnoe.xls", "bachelor", "mixed"),
    ("3-zaochnoe.xls", "bachelor", "distance"),
    ("4-ochnoe-mag.xls", "master", "fulltime"),
    ("5-ochno-zaochnoe-mag.xls", "master", "mixed"),
    ("6-zaochnoe-mag.xls", "master", "distance"),
]

DAYS = (
    ("понедельник", "mon"),
    ("вторник", "tue"),
    ("среда", "wed"),
    ("четверг", "thu"),
    ("пятница", "fri"),
    ("суббота", "sat"),
)

PAIRS = [8 * 60 + 40, 10 * 60 + 20, 12 * 60 + 10, 13 * 60 + 50, 15 * 60 + 30, 17 * 60 + 10, 18 * 60 + 50, 20 * 60 + 30]
EM = "\u2014"
TIME_RE = re.compile(r"(\d{1,2})[.:](\d{2})(?::\d{2})?\s*[-–" + EM + r"]\s*(\d{1,2})[.:](\d{2})")
TEACHER_RE = re.compile(
    r"Вакансия|[А-ЯЁ][а-яё]{2,}(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ]\.(?:\s*[А-ЯЁ]\.?)?"
)
WEEK_RE = re.compile(r"№\s*н(?:ед)?\.?\s*([0-9][0-9,\-\s–" + EM + r"]*)", re.I)


def norm(value):
    text = str(value or "").replace("\xa0", " ").replace("\n", " ")
    text = re.sub(
        r"(?<![А-ЯЁа-яё])(?:[А-ЯЁа-яё]\s){3,}[А-ЯЁа-яё](?![А-ЯЁа-яё])",
        lambda match: match.group(0).replace(" ", ""),
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


def day_key(value):
    text = norm(value).lower().replace("ё", "е")
    for name, key in DAYS:
        if text.startswith(name):
            return key
    return None


def clean_group(name):
    name = re.sub(r"\s*-\s*", "-", norm(name))
    return re.sub(r"\s+", " ", name).strip()


def parse_clock(text):
    dotted = []
    other = []
    for match in TIME_RE.finditer(text):
        start = int(match.group(1)) * 60 + int(match.group(2))
        label = "{:02d}:{:02d}–{:02d}:{:02d}".format(
            int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        )
        bucket = dotted if "." in match.group(0).split("-")[0].split("–")[0].split(EM)[0] else other
        bucket.append((label, start))
    found = dotted or other
    return found[-1] if found else None


def pair_number(minutes):
    best = min(range(len(PAIRS)), key=lambda index: abs(PAIRS[index] - minutes))
    if abs(PAIRS[best] - minutes) <= 40:
        return best + 1
    return max(1, min(8, 1 + minutes // 90))


def week_list(spec):
    weeks = []
    for part in re.split(r"[,;]", spec.replace("–", "-").replace(EM, "-")):
        part = part.strip()
        span = re.match(r"(\d+)\s*-\s*(\d+)$", part)
        if span:
            start, end = int(span.group(1)), int(span.group(2))
            if start > end:
                start, end = end, start
            if end - start <= 40:
                weeks.extend(range(start, end + 1))
        elif part.isdigit():
            weeks.append(int(part))
    return sorted({week for week in weeks if 1 <= week <= 44})


def is_kind_paren(inner):
    low = inner.lower().replace(" ", "")
    return any(token in low for token in ("лек", "прак", "лаб", "пр.", "пр№", "№н", "№нед"))


def kinds_in(text):
    low = text.lower()
    found = []
    if re.search(r"лаб", low):
        found.append("лабораторная")
    if re.search(r"прак|пр\.", low):
        found.append("практика")
    if re.search(r"лек", low):
        found.append("лекция")
    return found


def peel_teacher(text):
    matches = list(TEACHER_RE.finditer(text))
    if not matches:
        return text.strip(" .;,-"), ""
    end = len(text)
    names = []
    for match in reversed(matches):
        gap = text[match.end():end]
        if re.fullmatch(r"[\s.;,]*", gap or ""):
            names.append(re.sub(r"\s+", " ", match.group(0)).strip())
            end = match.start()
        else:
            break
    if not names:
        return text.strip(" .;,-"), ""
    names.reverse()
    teacher = "; ".join(re.sub(r"\.\s+", ".", name) for name in names)
    return text[:end].strip(" .;,-"), teacher


def study_week(year, month, day):
    import datetime
    start_year = year if month >= 9 else year - 1
    start = datetime.date(start_year, 9, 1)
    monday = start - datetime.timedelta(days=start.weekday())
    current = datetime.date(year, month, day)
    return max(1, (current - monday).days // 7 + 1)


def extract_notes(text):
    notes = []
    patterns = (
        r"\d{2}\.\d{2}\.\d{4}\.?\s*[-–" + EM + r"]?\s*(?:перенос\s+на\s+\d{2}\.\d{2}\.\d{4}\.?)?",
        r"пары нет",
        r"с\s+\d{1,2}[.:]\d{2}",
    )
    cleaned = text
    for pattern in patterns:
        for match in list(re.finditer(pattern, cleaned, re.I)):
            note = norm(match.group(0))
            if note and note not in notes:
                notes.append(note)
    for note in notes:
        cleaned = cleaned.replace(note, " ")
    tidy = []
    for note in notes:
        note = re.sub(r"\s*[-–" + EM + r"]\s*$", "", note).strip(" .;")
        if note and note not in tidy:
            tidy.append(note)
    return norm(cleaned), "; ".join(tidy)


def parse_lesson_text(raw, fallback_week):
    text = norm(raw)
    if not text or text.lower() in ("н", "ч", "н.", "ч.", "н..", "ч.."):
        return []
    marker = None
    marked = re.match(r"^([нч])\s*\.+\s*", text, re.I)
    if marked:
        marker = "odd" if marked.group(1).lower() == "н" else "even"
        text = text[marked.end():]
    dates = list(re.finditer(r"(\d{2})\.(\d{2})\.(\d{4})", text))
    if len(dates) >= 2:
        lessons = []
        for index, match in enumerate(dates):
            end = dates[index + 1].start() if index + 1 < len(dates) else len(text)
            chunk = text[match.end():end]
            week = study_week(int(match.group(3)), int(match.group(2)), int(match.group(1)))
            for lesson in parse_lesson_text(chunk, marker or fallback_week):
                lesson.pop("week", None)
                lesson["weeks"] = [week]
                lessons.append(lesson)
        return lessons
    text, note = extract_notes(text)
    if not text or re.fullmatch(r"[нч.\s]+", text, re.I):
        return []
    parens = list(re.finditer(r"\(([^)]*)\)", text))
    kind_parens = [item for item in parens if is_kind_paren(item.group(1))]
    body = text
    clauses = []
    for item in reversed(kind_parens):
        clauses.append(item.group(1))
        body = body[: item.start()] + " " + body[item.end():]
    body = norm(body)
    subject, teacher = peel_teacher(body)
    if teacher:
        surname = teacher.split()[0]
        if surname and surname in subject:
            subject = subject.split(surname)[0]
    subject = norm(subject).strip(" .;,-")
    if len(subject) < 2:
        return []
    if not clauses:
        lesson = {"subject": subject, "week": marker or fallback_week or "both"}
        if teacher:
            lesson["teacher"] = teacher
        if note:
            lesson["note"] = note
        return [lesson]
    lessons = []
    for clause in reversed(clauses):
        for piece in re.split(r"\s*;\s*", clause):
            weeks = None
            found = WEEK_RE.search(piece)
            if found:
                weeks = week_list(found.group(1))
            kinds = kinds_in(piece)
            lesson = {"subject": subject}
            if kinds:
                lesson["kind"] = ", ".join(kinds)
            if teacher:
                lesson["teacher"] = teacher
            if weeks:
                lesson["weeks"] = weeks
            else:
                lesson["week"] = marker or fallback_week or "both"
            if note:
                lesson["note"] = note
            lessons.append(lesson)
    return lessons


def looks_like_room(text):
    text = norm(text)
    if not text or re.match(r"^[нч]\s*\.", text, re.I):
        return False
    if text.startswith("http"):
        return True
    if re.search(r"лек|прак|лаб|№н", text, re.I) and len(text) > 18:
        return False
    return len(text) <= 24


def clean_room(text):
    text = norm(text)
    if text.startswith("http"):
        return text
    return re.sub(r"\s*-\s*", "-", text)


def sheet_preface(sheet):
    parts = []
    for row in range(min(8, sheet.nrows)):
        for col in range(min(3, sheet.ncols)):
            parts.append(norm(sheet.cell_value(row, col)))
    return " ".join(parts)


FEEIU = {"ЭК", "МН", "ЭЭ", "АП", "ИС", "ИЭ", "ГП", "ДМ", "ЭП", "ФК", "БП", "УП"}
GTF = {"ГД", "ТМ", "ИП", "СМ", "СА", "ГИ", "МД", "ММ", "МЦ", "ПС"}


def faculty_of(group_name):
    match = re.match(r"([А-ЯЁ]+)", group_name.replace(" ", ""))
    code = match.group(1) if match else ""
    if code.endswith("м") and (code[:-1] in FEEIU or code[:-1] in GTF):
        code = code[:-1]
    if code in FEEIU:
        return "feeiu"
    if code in GTF:
        return "gtf"
    return None


def course_number(preface, group_name):
    match = re.search(r"(\d+)\s*курс", preface, re.I)
    if match:
        number = int(match.group(1))
        if 1 <= number <= 6:
            return number
    match = re.search(r"(\d{2})(?:оз|з|м)?\b", group_name.replace(" ", ""))
    if match:
        number = 2026 - (2000 + int(match.group(1))) + 1
        if 1 <= number <= 6:
            return number
    return None


def load_sheet(path, sheet):
    book = xlrd.open_workbook(path, formatting_info=True)
    grid = book.sheet_by_name(sheet.name)
    origin = {}
    for rlo, rhi, clo, chi in grid.merged_cells:
        for row in range(rlo, rhi):
            for col in range(clo, chi):
                origin[(row, col)] = (rlo, rhi, clo, chi)

    def span(row, col):
        return origin.get((row, col), (row, row + 1, col, col + 1))

    def cell_text(row, col):
        rlo, rhi, clo, chi = span(row, col)
        return norm(grid.cell_value(rlo, clo)), (rlo, rhi, clo, chi)

    header = None
    for row in range(grid.nrows):
        values = [norm(grid.cell_value(row, col)).lower() for col in range(grid.ncols)]
        if any(value.startswith("день") or value == "дни" for value in values) and any(
            value in ("время", "часы") for value in values
        ):
            header = row
            break
    if header is None:
        return {}, ""

    headers = [norm(grid.cell_value(header, col)) for col in range(grid.ncols)]
    day_cols = [col for col, value in enumerate(headers) if value.lower().startswith("дн")]
    time_cols = [col for col, value in enumerate(headers) if value.lower() in ("время", "часы")]
    groups = []
    col = 0
    while col < grid.ncols:
        title = headers[col]
        low = title.lower().rstrip(".")
        if not title or col in day_cols or col in time_cols or low in ("ауд", "аудитория"):
            col += 1
            continue
        room_col = None
        probe = col + 1
        while probe < grid.ncols and not headers[probe]:
            probe += 1
        if probe < grid.ncols and headers[probe].lower() in ("ауд", "аудитория"):
            room_col = probe
        groups.append({"name": clean_group(title), "col": col, "room": room_col})
        col = room_col + 1 if room_col is not None else col + 1

    day_col = day_cols[0] if day_cols else 0
    row_day = {}
    row_time = {}
    for row in range(header + 1, grid.nrows):
        day_text, _ = cell_text(row, day_col)
        row_day[row] = day_key(day_text)
        clocks = []
        for time_col in time_cols:
            text, _ = cell_text(row, time_col)
            clock = parse_clock(text)
            if not clock:
                continue
            dotted = bool(re.search(r"\d\.\d{2}", text))
            clocks.append((dotted, clock))
        dotted_clocks = [clock for dotted, clock in clocks if dotted]
        row_time[row] = (dotted_clocks or [clock for _, clock in clocks] or [None])[0]

    def row_role(row):
        found = set()
        for col in range(grid.ncols):
            rlo, rhi, clo, chi = span(row, col)
            if (rlo, clo) != (row, col):
                continue
            match = re.match(r"^([нч])\s*\.", norm(grid.cell_value(rlo, clo)), re.I)
            if match:
                found.add("odd" if match.group(1).lower() == "н" else "even")
        if found == {"odd"}:
            return "odd"
        if found == {"even"}:
            return "even"
        return None

    def fallback_week(rlo, rhi):
        roles = [row_role(row) for row in range(rlo, rhi)]
        roles = [role for role in roles if role]
        if "odd" in roles and "even" in roles:
            return "both"
        if roles == ["odd"]:
            return "odd"
        if roles == ["even"]:
            return "even"
        times = [row_time[row][0] if row_time.get(row) else None for row in range(max(header + 1, rlo - 3), min(grid.nrows, rhi + 3))]
        # Rows of this slot share one clock label.
        label = None
        for row in range(rlo, rhi):
            if row_time.get(row):
                label = row_time[row][0]
                break
        if not label:
            return "both"
        block = [row for row in range(header + 1, grid.nrows) if row_time.get(row) and row_time[row][0] == label and row_day.get(row) == row_day.get(rlo)]
        if len(block) >= 2 and rhi - rlo >= len(block):
            return "both"
        if len(block) == 2 and rlo in block:
            return "odd" if block.index(rlo) == 0 else "even"
        if len(block) == 1:
            return "both"
        return "both"

    def find_room(rlo, rhi, clo, chi, room_col):
        columns = []
        if room_col is not None and not (clo <= room_col < chi):
            columns.append(room_col)
        if chi < grid.ncols:
            columns.append(chi)
        for col in columns:
            for row in range(rlo, rhi):
                r0, r1, c0, c1 = span(row, col)
                if c0 == clo and r0 == rlo:
                    continue
                text = norm(grid.cell_value(r0, c0))
                if looks_like_room(text):
                    return clean_room(text)
        return ""

    lessons_by_group = {group["name"]: [] for group in groups}
    seen = set()
    for row in range(header + 1, grid.nrows):
        for col in range(grid.ncols):
            rlo, rhi, clo, chi = span(row, col)
            if (rlo, clo) in seen or (row, col) != (rlo, clo):
                continue
            seen.add((rlo, clo))
            covered = [group for group in groups if clo <= group["col"] < chi]
            if not covered:
                continue
            day = row_day.get(rlo)
            clock = None
            for probe in range(rlo, rhi):
                if row_time.get(probe):
                    clock = row_time[probe]
                    break
            if not day or not clock:
                continue
            raw = grid.cell_value(rlo, clo)
            parsed = parse_lesson_text(raw, fallback_week(rlo, rhi))
            if not parsed:
                continue
            room = find_room(rlo, rhi, clo, chi, covered[0]["room"])
            label, minutes = clock
            for group in covered:
                for item in parsed:
                    lesson = {
                        "pair": pair_number(minutes),
                        "time": label,
                        "subject": item["subject"],
                        "day": day,
                    }
                    for key in ("kind", "teacher", "week", "weeks", "note"):
                        if item.get(key):
                            lesson[key] = item[key]
                    if room:
                        lesson["room"] = room
                    lessons_by_group[group["name"]].append(lesson)
    return lessons_by_group, sheet_preface(grid)


def merge_weeks(lessons):
    grouped = {}
    order = []
    for lesson in lessons:
        key = (
            lesson["day"],
            lesson["pair"],
            lesson["time"],
            lesson["subject"],
            lesson.get("kind", ""),
            lesson.get("teacher", ""),
            lesson.get("room", ""),
            lesson.get("note", ""),
            tuple(lesson["weeks"]) if lesson.get("weeks") else None,
        )
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(lesson.get("week"))
    merged = []
    for key in order:
        weeks = grouped[key]
        lesson = {
            "day": key[0],
            "pair": key[1],
            "time": key[2],
            "subject": key[3],
        }
        if key[4]:
            lesson["kind"] = key[4]
        if key[5]:
            lesson["teacher"] = key[5]
        if key[6]:
            lesson["room"] = key[6]
        if key[7]:
            lesson["note"] = key[7]
        if key[8]:
            lesson["weeks"] = list(key[8])
        else:
            marks = set(weeks)
            if "both" in marks or ({"odd", "even"} <= marks):
                lesson["week"] = "both"
            elif "odd" in marks:
                lesson["week"] = "odd"
            elif "even" in marks:
                lesson["week"] = "even"
            else:
                lesson["week"] = "both"
        merged.append(lesson)
    # Одна и та же пара из двух листов: оставляем запись с аудиторией.
    best = {}
    order = []
    for lesson in merged:
        key = (
            lesson["day"], lesson["pair"], lesson["time"], lesson["subject"],
            lesson.get("kind", ""), lesson.get("teacher", ""), lesson.get("note", ""),
            lesson.get("week", ""), tuple(lesson.get("weeks") or []),
        )
        if key not in best:
            best[key] = lesson
            order.append(key)
            continue
        if lesson.get("room") and not best[key].get("room"):
            best[key] = lesson
    return [best[key] for key in order]


def main():
    groups = {}
    for filename, level, form in FILES:
        path = os.path.join(FOLDER, filename)
        book = xlrd.open_workbook(path, formatting_info=False)
        for sheet in book.sheets():
            found, preface = load_sheet(path, sheet)
            for name, lessons in found.items():
                course = course_number(preface, name)
                faculty = faculty_of(name)
                if not course or not faculty:
                    if name and not faculty and re.search(r"\d", name):
                        print("без факультета:", name)
                    continue
                key = (level, form, faculty, name)
                bucket = groups.setdefault(key, {
                    "name": name,
                    "course": course,
                    "level": level,
                    "form": form,
                    "faculty": faculty,
                    "lessons": [],
                })
                bucket["lessons"].extend(lessons)
                bucket["course"] = course

    payload = []
    for key in sorted(groups, key=lambda item: (item[0], item[1], item[2], groups[item]["course"], item[3])):
        bucket = groups[key]
        days = {day: [] for _, day in DAYS}
        for lesson in merge_weeks(bucket["lessons"]):
            day = lesson.pop("day")
            days[day].append(lesson)
        for day in days:
            days[day].sort(key=lambda item: (item["pair"], item["subject"]))
        days = {day: items for day, items in days.items() if items}
        payload.append({
            "name": bucket["name"],
            "course": bucket["course"],
            "level": bucket["level"],
            "form": bucket["form"],
            "faculty": bucket["faculty"],
            "days": days,
        })

    downloads = {
        "bachelor": {
            "fulltime": "../Осень 2026-27 расписание/1-ochnoe.xls",
            "mixed": "../Осень 2026-27 расписание/2-ochno-zaochnoe.xls",
            "distance": "../Осень 2026-27 расписание/3-zaochnoe.xls",
        },
        "master": {
            "fulltime": "../Осень 2026-27 расписание/4-ochnoe-mag.xls",
            "mixed": "../Осень 2026-27 расписание/5-ochno-zaochnoe-mag.xls",
            "distance": "../Осень 2026-27 расписание/6-zaochnoe-mag.xls",
        },
    }
    text = "window.SCHEDULE = " + json.dumps({"downloads": downloads, "groups": payload}, ensure_ascii=False, indent=2) + ";\n"
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(text)
    lessons = sum(len(items) for group in payload for items in group["days"].values())
    print("groups", len(payload), "lessons", lessons)
    for group in payload:
        if group["name"] in ("ИС-26", "ЭЭ-26оз", "БПм-25оз"):
            print("---", group["name"], group["level"], group["form"], "course", group["course"])
            for day, items in group["days"].items():
                for item in items[:4]:
                    print(" ", day, item.get("time"), item.get("week") or item.get("weeks"), item["subject"][:60], item.get("room", ""))


if __name__ == "__main__":
    main()
