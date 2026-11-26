import json
import random
import re
import urllib.parse
import urllib.request
from pathlib import Path

DATA_PATH = Path("extra_puzzles.json")

WIKI_CATEGORIES = [
    "Категория:Русские_существительные",
    "Категория:Экономические_термины",
    "Категория:Шахматные_термины",
    "Категория:Футбольная_терминология",
    "Категория:Психологические_термины",
    "Категория:Информационные_технологии",
    "Категория:Кинематографические_термины",
    "Категория:Философские_термины",
]

CYR_5_6_RE = re.compile(r"^[А-Я]{5,6}$")
CYR_4_RE = re.compile(r"^[А-Я]{4}$")


def fetch_wiktionary_words(category: str, limit: int = 250) -> list[str]:
    # Случайная стартовая буква, чтобы каждый запуск собирал новые слова
    start_letter = random.choice("АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЭЮЯ")
    params = urllib.parse.urlencode({
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmnamespace": 0,
        "cmlimit": limit,
        "cmstartsortkeyprefix": start_letter,
        "format": "json",
    })
    url = f"https://ru.wiktionary.org/w/api.php?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "borevichh-quiz-updater/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        members = payload.get("query", {}).get("categorymembers", [])
        return [m["title"].strip().upper().replace("Ё", "Е") for m in members if "title" in m]
    except Exception as exc:
        print(f"Skip {category}: {exc}")
        return []


def load_existing() -> dict:
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"words5": [], "words6": [], "tangle4": [], "cryptograms": [], "wordchains": []}


def main() -> None:
    db = load_existing()
    words5 = set(db.get("words5", []))
    words6 = set(db.get("words6", []))
    tangle4 = set(db.get("tangle4", []))

    for cat in WIKI_CATEGORIES:
        raw_titles = fetch_wiktionary_words(cat, limit=250)
        for w in raw_titles:
            if CYR_5_6_RE.match(w):
                if len(w) == 5:
                    words5.add(w)
                elif len(w) == 6:
                    words6.add(w)
            elif CYR_4_RE.match(w):
                tangle4.add(w)

    # Ограничиваем разумный размер файла (до 1500 слов каждого типа), сохраняя свежесть
    db["words5"] = sorted(words5)[-1500:]
    db["words6"] = sorted(words6)[-1500:]
    db["tangle4"] = sorted(tangle4)[-800:]

    DATA_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated: words5={len(db['words5'])}, words6={len(db['words6'])}, tangle4={len(db['tangle4'])}")


if __name__ == "__main__":
    main()
