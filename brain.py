"""
brain.py — Локальный движок ответов, обученный на реальных диалогах ботов.
Не требует никаких API. Работает полностью оффлайн.

Логика:
1. Загружает dialogs_timur.txt и dialogs_alibek.txt при первом вызове
2. При запросе ищет похожее входящее по ключевым словам → возвращает реальный ответ
3. Если похожего нет — возвращает None (тогда phrases.py или AI)

Использование:
    from brain import get_brain_reply
    reply = get_brain_reply("timur", her_text, history)
    if reply:
        return reply
"""

import re
import random
import os
from collections import defaultdict
from typing import Optional


# ──────────────────────────────────────────────
# ЗАГРУЗКА ДИАЛОГОВ
# ──────────────────────────────────────────────

def _load_pairs(filename: str) -> list[tuple[str, str]]:
    """
    Читает dialogs_*.txt и возвращает список пар (её_сообщение, ответ_бота).
    Формат строки: "2026-05-28 09:05 | CHAT:123 | ONA | текст"
    """
    pairs = []
    if not os.path.exists(filename):
        return pairs
    try:
        lines = open(filename, encoding="utf-8").readlines()
    except Exception:
        return pairs

    by_chat: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for line in lines:
        parts = line.strip().split(" | ")
        if len(parts) < 4:
            continue
        _, chat_raw, role_raw, *text_parts = parts
        chat_id = chat_raw.replace("CHAT:", "").strip()
        role = "bot" if role_raw.strip() == "BOT" else "ona"
        text = " | ".join(text_parts).strip()
        if text:
            by_chat[chat_id].append((role, text))

    for chat_id, msgs in by_chat.items():
        for i in range(len(msgs) - 1):
            role_a, text_a = msgs[i]
            role_b, text_b = msgs[i + 1]
            if role_a == "ona" and role_b == "bot":
                her = text_a.split(" / ")[0].strip()
                bot = text_b.split(" / ")[0].strip()
                if her and bot and len(her) > 1 and len(bot) > 1:
                    pairs.append((her, bot))

    return pairs


# ──────────────────────────────────────────────
# ТОКЕНИЗАЦИЯ
# ──────────────────────────────────────────────

_STOPWORDS = {
    "и", "в", "на", "с", "по", "за", "к", "из", "у", "от", "до", "о",
    "а", "но", "уже", "ещё", "так",
    "вы", "ты", "я", "мы", "он", "она", "они", "вас", "вам", "меня",
    "мне", "его", "её", "их", "им", "нас", "нам", "да", "нет",
    "ну", "же", "бы", "ли",
}


def _tokenize(text: str) -> set[str]:
    t = text.lower()
    t = re.sub(r'[^\w\s]', ' ', t)
    tokens = set(t.split()) - _STOPWORDS
    return tokens if tokens else set(t.split())  # если всё выбросили — вернём оригинал


# ──────────────────────────────────────────────
# ИНДЕКС (глобальный, ленивая загрузка)
# ──────────────────────────────────────────────

# Структура: persona → список (her_text, bot_reply, her_tokens)
_INDEX: dict[str, list[tuple[str, str, set[str]]]] = {"timur": [], "alibek": []}
_MTIME: dict[str, float] = {}
_FILES = {
    "timur": "dialogs_timur.txt",
    "alibek": "dialogs_alibek.txt",
}


def _ensure(persona: str):
    """Загружает/перезагружает индекс если файл изменился."""
    fname = _FILES.get(persona)
    if not fname:
        return
    try:
        mtime = os.path.getmtime(fname)
    except OSError:
        return
    if _MTIME.get(persona) == mtime:
        return  # уже актуален
    pairs = _load_pairs(fname)
    _INDEX[persona] = [(her, bot, _tokenize(her)) for her, bot in pairs]
    _MTIME[persona] = mtime


# ──────────────────────────────────────────────
# ПОИСК
# ──────────────────────────────────────────────

def get_brain_reply(
    persona: str,
    her_text: str,
    history: list = None,
    min_score: int = 1,
) -> Optional[str]:
    """
    persona: "timur" или "alibek"
    her_text: последнее сообщение девушки
    history: список (role, text) — для антиповтора
    min_score: минимальное количество совпавших токенов (1 = хотя бы одно)

    Возвращает str или None.
    """
    _ensure(persona)

    pairs = _INDEX.get(persona, [])
    if not pairs:
        return None

    # Слишком короткий запрос — пропускаем (phrases.py справится)
    if len(her_text.strip()) < 3:
        return None

    query_tokens = _tokenize(her_text)
    if not query_tokens:
        return None

    # Антиповтор
    exclude: set[str] = set()
    if history:
        exclude = {text.lower().strip() for role, text in history[-30:] if role == "assistant"}

    # Ищем совпадения
    candidates: list[tuple[int, str]] = []
    for her, bot, tokens in pairs:
        sc = len(query_tokens & tokens)
        if sc >= min_score:
            if bot.lower().strip() not in exclude:
                candidates.append((sc, bot))

    if not candidates:
        return None

    # Берём группу с наибольшим баллом
    max_score = max(sc for sc, _ in candidates)
    best = [bot for sc, bot in candidates if sc == max_score]

    return random.choice(best)


def get_brain_stats() -> dict:
    """Статистика по загруженным диалогам."""
    for p in ("timur", "alibek"):
        _ensure(p)
    return {
        "timur_pairs": len(_INDEX["timur"]),
        "alibek_pairs": len(_INDEX["alibek"]),
    }


if __name__ == "__main__":
    stats = get_brain_stats()
    print(f"Загружено пар — Тимур: {stats['timur_pairs']}, Алибек: {stats['alibek_pairs']}")

    tests = [
        ("Как дела?", "timur"),
        ("Куда пойдём?", "timur"),
        ("Привет", "timur"),
        ("Ты бот?", "timur"),
        ("Странно разговариваешь", "timur"),
        ("Расскажи о себе", "timur"),
        ("Откуда ты", "timur"),
    ]
    for t, p in tests:
        r = get_brain_reply(p, t)
        print(f"  {t!r} → {r!r}")
