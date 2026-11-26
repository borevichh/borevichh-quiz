import json
import random
import urllib.request
from pathlib import Path

OUT_PATH = Path("lichess_puzzles.json")

# Официальный датасет Lichess (6.16M задач) на Hugging Face + API дневных задач Lichess
HF_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows"
    "?dataset=Lichess%2Fchess-puzzles&config=default&split=train"
    "&offset={offset}&length=100"
)
DAILY_URL = "https://lichess.org/api/puzzle/daily"

THEME_NAMES_RU = {
    "mateIn1": "Мат в 1 ход",
    "mateIn2": "Мат в 2 хода",
    "mateIn3": "Мат в 3 хода",
    "fork": "Двойной удар (вилка)",
    "pin": "Связка",
    "skewer": "Линейный удар",
    "sacrifice": "Жертва",
    "discoveredAttack": "Вскрытое нападение",
    "backRankMate": "Мат по последней горизонтали",
    "endgame": "Эндшпиль",
    "middlegame": "Миттельшпиль",
    "crushing": "Решающий перевес",
    "advantage": "Выигрыш материала",
    "quietMove": "Тихий ход",
    "deflection": "Отвлечение",
    "attraction": "Завлечение",
}


def translate_themes(raw_themes: str) -> str:
    if not raw_themes:
        return "Тактика Lichess"
    parts = raw_themes.split()
    ru = [THEME_NAMES_RU[t] for t in parts if t in THEME_NAMES_RU]
    return " • ".join(ru[:2]) if ru else "Тактика Lichess"


def load_existing() -> list[dict]:
    if OUT_PATH.exists():
        try:
            data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def fetch_hf_batch(offset: int) -> list[dict]:
    url = HF_ROWS_URL.format(offset=offset)
    req = urllib.request.Request(url, headers={"User-Agent": "borevichh-lichess-sync/1.0"})
    puzzles = []
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        for item in payload.get("rows", []):
            row = item.get("row", {})
            pid = row.get("PuzzleId")
            fen = row.get("FEN")
            moves_str = row.get("Moves", "")
            rating = int(row.get("Rating", 1200))
            themes = row.get("Themes", "")
            moves = moves_str.strip().split()
            # В базе Lichess moves[0] — ход соперника перед началом задачи, moves[1:] — решение игрока и ответы
            if pid and fen and len(moves) >= 3:
                puzzles.append({
                    "id": pid,
                    "fen": fen,
                    "moves": moves,
                    "rating": rating,
                    "theme": translate_themes(themes),
                })
    except Exception as exc:
        print(f"HF batch error at offset {offset}: {exc}")
    return puzzles


def fetch_daily() -> list[dict]:
    req = urllib.request.Request(
        DAILY_URL,
        headers={"Accept": "application/json", "User-Agent": "borevichh-lichess-sync/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        puz = data.get("puzzle", {})
        game = data.get("game", {})
        # Daily API возвращает PGN; используем если есть начальный FEN
        if puz.get("id") and puz.get("solution") and game.get("fen"):
            return [{
                "id": puz["id"],
                "fen": game["fen"],
                "moves": puz["solution"],
                "rating": int(puz.get("rating", 1500)),
                "theme": translate_themes(" ".join(puz.get("themes", []))),
            }]
    except Exception as exc:
        print(f"Daily fetch skipped: {exc}")
    return []


def main() -> None:
    existing = load_existing()
    by_id = {p["id"]: p for p in existing if "id" in p}

    # Берем 4 случайных среза из 6-миллионной базы Lichess (400 новых задач за запуск)
    for _ in range(4):
        offset = random.randint(0, 5_000_000)
        for p in fetch_hf_batch(offset):
            by_id[p["id"]] = p

    for p in fetch_daily():
        by_id[p["id"]] = p

    all_puzzles = list(by_id.values())
    random.shuffle(all_puzzles)
    # Храним до 2500 отобранных задач в JSON (~350 КБ — грузится мгновенно)
    trimmed = all_puzzles[:2500]
    OUT_PATH.write_text(json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Saved {len(trimmed)} Lichess puzzles to {OUT_PATH}")


if __name__ == "__main__":
    main()
