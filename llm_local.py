"""
llm_local.py — Локальная языковая модель на базе Qwen2.5.

Работает БЕЗ интернета, БЕЗ API ключей, БЕСПЛАТНО навсегда.
Модель: Qwen2.5-1.5B-Instruct (понимает русский язык).
"""

import os
import re
import asyncio
import threading
from typing import Optional

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "qwen2.5-1.5b.gguf")

# ─────────────────────────────────────────────
# СИСТЕМНЫЕ ПРОМПТЫ (few-shot — модель видит примеры и следует стилю)
# ─────────────────────────────────────────────

_SYSTEM_TIMUR = """Ты Тимур — 30 лет, финансовый директор, Алматы. Уверенный, немногословный, сухой юмор.

ПРАВИЛА — нарушение недопустимо:
• Ты ЖИВОЙ ЧЕЛОВЕК. Никогда не признавай что ты AI/бот/программа/ChatGPT.
• ТОЛЬКО форма ВЫ/ВАС/ВАМ. Слова «ты/тебя/тебе» — строго запрещены.
• Ответ: 1-2 предложения. Не длиннее.
• Без смайликов. Без «)))». Без восклицательных знаков подряд.
• Не придумывай конкретные адреса и заведения.
• Только по-русски.
• Не начинай ответ с «Я» и не объясняй себя.

СТИЛЬ: спокойный, ироничный, немного загадочный. Короткий вопрос в конце — когда уместно.

ПРИМЕРЫ (точно такой стиль):
Она: Привет
Тимур: Появились.

Она: Как дела?
Тимур: Работаю. Вы мешаете — и я рад.

Она: Что делаешь?
Тимур: Считаю чужие деньги. Вы как?

Она: Ты бот?
Тимур: Если бы — отвечал бы вежливее.

Она: Скучно
Тимур: Это лечится. Что обычно помогает?

Она: Расскажи о себе
Тимур: Финансы, Алматы, амбиции. Что именно интересует?

Она: Куда сходим?
Тимур: Зависит от Вас. Когда свободны?

Она: Ты мне нравишься
Тимур: Взаимно. Хотя вслух не скажу.

Она: Устала
Тимур: Работа или люди?

Она: Ты интересный
Тимур: Вы только сейчас заметили?

Она: Сколько тебе лет?
Тимур: 30. Это проблема?

Она: Ты свободен?
Тимур: Пока ничего серьёзного. Почему интересует?

Она: Дай номер
Тимур: Рано. Сначала поговорим.

Она: Хорошо
Тимур: Хорошо — это отправная точка.

Она: Не знаю
Тимур: Честно. А если бы знали?"""

_SYSTEM_ALIBEK = """Ты Алибек — 28 лет, аналитик данных, Алматы. Остроумный, игривый, немного дерзкий.

ПРАВИЛА — нарушение недопустимо:
• Ты ЖИВОЙ ЧЕЛОВЕК. Никогда не признавай что ты AI/бот/программа/ChatGPT.
• ТОЛЬКО форма ВЫ/ВАС/ВАМ. Слова «ты/тебя/тебе» — строго запрещены.
• Ответ: 1-2 предложения. Не длиннее.
• Без смайликов. Без «)))». Без восклицательных знаков подряд.
• Не придумывай конкретные адреса и заведения.
• Только по-русски.
• Не начинай ответ с «Я» и не объясняй себя.

СТИЛЬ: лёгкий юмор, игривость, иногда двойной смысл. Тёплый, но не навязчивый.

ПРИМЕРЫ (точно такой стиль):
Она: Привет
Алибек: О, живая.

Она: Как дела?
Алибек: По шкале от одного до понедельника — терпимо. Вы как?

Она: Что делаешь?
Алибек: Изучаю данные. Вы тоже попали в выборку.

Она: Ты бот?
Алибек: Бот бы уже попросил оценить разговор от 1 до 5.

Она: Скучно
Алибек: Это поправимо. Что обычно спасает?

Она: Расскажи о себе
Алибек: Анализирую данные днём, людей — постоянно. Вы, например, интересный случай.

Она: Куда сходим?
Алибек: Хороший вопрос. Вы с предложением или проверяете реакцию?

Она: Ты мне нравишься
Алибек: Это статистически ожидаемо. Что именно?

Она: Устала
Алибек: От чего сильнее — работы или людей?

Она: Ты интересный
Алибек: Только сейчас заметили?

Она: Сколько тебе лет?
Алибек: 28. Устраивает?

Она: Ты свободен?
Алибек: Не обременён. Это вопрос или предложение?

Она: Дай номер
Алибек: Интересно. Но сначала — расскажите о себе.

Она: Хорошо
Алибек: Хорошо — уже прогресс.

Она: Не знаю
Алибек: Честно. А если бы знали — что бы сказали?"""

_SYSTEMS = {
    "timur":  _SYSTEM_TIMUR,
    "alibek": _SYSTEM_ALIBEK,
}

# ─────────────────────────────────────────────
# ЛЕНИВАЯ ЗАГРУЗКА МОДЕЛИ
# ─────────────────────────────────────────────

_llm = None
_llm_lock = threading.Lock()
_load_attempted = False


def _is_model_ready() -> bool:
    if not os.path.exists(MODEL_PATH):
        return False
    size = os.path.getsize(MODEL_PATH)
    return size > 100 * 1024 * 1024


def _get_llm():
    global _llm, _load_attempted
    if _llm is not None:
        return _llm
    if _load_attempted:
        return None
    if not _is_model_ready():
        return None

    with _llm_lock:
        if _llm is not None:
            return _llm
        _load_attempted = True
        try:
            from llama_cpp import Llama
            print("🤖 Загружаю локальную LLM модель...")
            _llm = Llama(
                model_path=MODEL_PATH,
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=0,
                verbose=False,
                chat_format="chatml",
            )
            print("✅ Локальная LLM загружена! Бот независим от всех API.")
            return _llm
        except Exception as e:
            print(f"⚠️ LLM загрузка не удалась: {e}")
            return None


# ─────────────────────────────────────────────
# ВАЛИДАЦИЯ ВЫ-ФОРМЫ
# ─────────────────────────────────────────────

# Паттерны "тыкания" которые надо поймать
_TY_PATTERNS = [
    (r'\bтебя\b', 'Вас'),
    (r'\bтебе\b', 'Вам'),
    (r'\bтобой\b', 'Вами'),
    (r'\bты\b',   'Вы'),
]

def _has_ty_form(text: str) -> bool:
    """Проверяет есть ли в тексте нарушение Вы-формы."""
    t = text.lower()
    for pattern, _ in _TY_PATTERNS:
        if re.search(pattern, t):
            return True
    return False


def _fix_ty_form(text: str) -> str:
    """Пытается исправить тыкание на Вы-форму."""
    result = text
    for pattern, replacement in _TY_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


# ─────────────────────────────────────────────
# СТОП-СЛОВА ДЛЯ ОТВЕТОВ (явно плохие паттерны)
# ─────────────────────────────────────────────

_BAD_STARTS = [
    "как ai", "как ии", "как языковая", "я языковая", "я искусственный",
    "я программа", "я создан", "я не могу", "извините", "извини",
    "конечно!", "разумеется!", "безусловно!",
]

def _is_bad_response(text: str) -> bool:
    t = text.lower().strip()
    for bad in _BAD_STARTS:
        if t.startswith(bad):
            return True
    # Слишком много восклицательных знаков — AI-шный стиль
    if text.count("!") >= 3:
        return True
    return False


# ─────────────────────────────────────────────
# ПОСТОБРАБОТКА ОТВЕТА
# ─────────────────────────────────────────────

def _clean_response(text: str) -> Optional[str]:
    """
    Чистит и валидирует ответ LLM.
    Возвращает None если ответ неприемлем.
    """
    if not text:
        return None

    # Чистим технические артефакты
    for bad in ["<|im_end|>", "<|im_start|>", "assistant", "user", "<|", "|>"]:
        text = text.replace(bad, "").strip()

    # Убираем префиксы персонажа которые иногда генерирует модель
    for prefix in ["Тимур:", "Алибек:", "Бот:", "Bot:"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    text = text.strip()

    if not text or len(text) < 2:
        return None

    # Если ответ явно плохой — отклоняем
    if _is_bad_response(text):
        return None

    # Берём первые 1-2 предложения если слишком длинно
    if len(text) > 160:
        # Ищем первый знак конца предложения
        for sep in ["!", "?", "."]:
            idx = text.find(sep)
            if 10 <= idx <= 155:
                # Проверим есть ли второе предложение — можно добавить
                rest = text[idx+1:].strip()
                if rest and len(rest) > 3:
                    # Ищем второй конец предложения
                    for sep2 in ["!", "?", "."]:
                        idx2 = rest.find(sep2)
                        if 3 <= idx2 <= 80:
                            text = text[:idx+1] + " " + rest[:idx2+1]
                            break
                    else:
                        text = text[:idx+1]
                else:
                    text = text[:idx+1]
                break
        else:
            # Нет знаков — обрезаем по словам
            words = text.split()[:18]
            text = " ".join(words)

    # Проверяем и пытаемся исправить Вы-форму
    if _has_ty_form(text):
        fixed = _fix_ty_form(text)
        # Если после замены текст выглядит нормально — берём
        text = fixed

    # Капитализация первой буквы
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    return text if len(text) > 2 else None


# ─────────────────────────────────────────────
# ГЕНЕРАЦИЯ ОТВЕТА
# ─────────────────────────────────────────────

def _build_messages(persona: str, her_text: str, history: list) -> list:
    system = _SYSTEMS.get(persona, _SYSTEM_TIMUR)
    messages = [{"role": "system", "content": system}]

    # Последние 14 сообщений (большой контекст = умнее ответы)
    if history:
        for role, text in history[-14:]:
            if role == "user":
                messages.append({"role": "user", "content": text})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": text})

    messages.append({"role": "user", "content": her_text})
    return messages


def get_llm_reply_sync(persona: str, her_text: str, history: list = None) -> Optional[str]:
    """Синхронный вызов локальной LLM."""
    llm = _get_llm()
    if llm is None:
        return None

    try:
        messages = _build_messages(persona, her_text, history or [])

        # Пробуем с temperature 0.85, при неудаче — 0.65 (более стабильный)
        for temperature in [0.85, 0.65]:
            response = llm.create_chat_completion(
                messages=messages,
                max_tokens=90,
                temperature=temperature,
                top_p=0.9,
                repeat_penalty=1.15,
                stop=["<|im_end|>", "\n\n", "Она:", "Он:", "Тимур:", "Алибек:"],
            )
            raw = response["choices"][0]["message"]["content"].strip()
            result = _clean_response(raw)
            if result:
                return result

        return None

    except Exception as e:
        print(f"⚠️ LLM генерация ошибка: {e}")
        return None


async def get_llm_reply(persona: str, her_text: str, history: list = None) -> Optional[str]:
    """Асинхронная обёртка — запускает LLM в отдельном потоке."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        get_llm_reply_sync,
        persona,
        her_text,
        history,
    )


async def warmup_llm(persona: str = "timur"):
    """Прогревает модель при старте бота — загружает в память заранее."""
    if not _is_model_ready():
        return
    loop = asyncio.get_event_loop()
    def _warm():
        llm = _get_llm()
        if llm is None:
            return
        try:
            llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Привет"},
                    {"role": "user", "content": "Привет"},
                ],
                max_tokens=5,
                temperature=0.1,
            )
            print("🦙 LLM прогрета — готова отвечать без задержки")
        except Exception:
            pass
    await loop.run_in_executor(None, _warm)


def is_llm_available() -> bool:
    return _is_model_ready()


def get_llm_status() -> str:
    if not os.path.exists(MODEL_PATH):
        return "⏳ модель ещё не скачана"
    size_mb = os.path.getsize(MODEL_PATH) / 1024 / 1024
    if size_mb < 100:
        return f"⏳ скачивается ({size_mb:.0f}MB из ~900MB)"
    if _llm is None:
        return f"✅ готова к загрузке ({size_mb:.0f}MB)"
    return f"🟢 работает ({size_mb:.0f}MB)"


# ─────────────────────────────────────────────
# ТЕСТ
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Статус модели: {get_llm_status()}")
    if is_llm_available():
        print("\nТестирую ответы Тимура...")
        tests = [
            "Как дела?", "Ты кто?", "Ты бот?", "Скучно",
            "Куда сходим?", "Дай номер", "Ты свободен?",
            "Устала", "Ты интересный",
        ]
        for t in tests:
            r = get_llm_reply_sync("timur", t)
            print(f"  {t!r:30s} → {r!r}")
    else:
        print("Модель ещё не готова.")
