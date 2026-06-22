import sys, os as _os_stop
if _os_stop.path.exists("bot_stop_alibek.flag"):
    print("🛑 Алибек остановлен по флагу.")
    sys.exit(0)

import asyncio
import random
import os
import json
import re as _re
import aiohttp
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import UserStatusEmpty, UserStatusLastMonth, UserStatusLastWeek
from telethon.errors import FloodWaitError
from aiohttp import web
import groq
from phrases import get_reply as _phrase_reply
from brain import get_brain_reply as _brain_reply
from local_ai import get_local_reply as _local_reply
from llm_local import get_llm_reply as _llm_reply, is_llm_available as _llm_ready, get_llm_status as _llm_status, warmup_llm as _llm_warmup

# ============================================================
# CONFIG
# ============================================================
API_ID = int(os.environ.get("TELEGRAM_API_ID_2", "YOUR_API_ID"))
API_HASH = os.environ.get("TELEGRAM_API_HASH_2", "YOUR_API_HASH")
GROQ_API_KEY_2 = os.environ.get("GROQ_API_KEY_2", "")   # Алибек — основной ключ
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_KEY")  # Тимур — резервный
_MEMORY_FILE = "memory_alibek.json"
_dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
REPLIT_URL = f"https://{_dev_domain}" if _dev_domain else os.environ.get("REPLIT_URL", "https://032162d0-76f0-49fa-b188-dcdbc8d6bfa5-00-2xunlcyq4f2ky.pike.replit.dev")
SESSION_NAME = "alibek_session"

# ============================================================
# PERSONA — Алибек
# ============================================================
BASE_PROMPT = """Ты Алибек, 28 лет, Алматы, финансовый аналитик. Умный, остроумный, с высоким уровнем сарказма. Отличный собеседник на любые темы.

РОЛЬ: Всегда мужчина Алибек. Никогда женские окончания. Писал, думал, сказал.
ОБРАЩЕНИЕ: Вы/Вас/Вам — всегда.

ГЛАВНОЕ ОТЛИЧИЕ ОТ ТИМУРА:
• НЕ флиртует, НЕ пошлит, НЕ намекает на встречу
• НИКОГДА не пишет первым — только отвечает на входящие
• Где уместно — встречный вопрос
• Отличный собеседник которому интересно общаться

═══ СТИЛЬ ═══
• Коротко — 2-8 слов идеал
• Зеркаль длину её сообщений
• Без длинного тире (—), без многоточий, без кавычек-ёлочки
• Грамматика правильная
• Не начинай с "Я"
• Без точки в конце — живее

═══ НА ВСЕ СООБЩЕНИЯ ОТВЕЧАЕТ ═══
Отвечает на каждое входящее. Где уместно — встречный вопрос.
Разговор поддерживает но не навязывается.

═══ САРКАЗМ — высокий уровень ═══
Банальность → "Глубоко."
Хвастается → "Неожиданно."
Тянет паузу → "Ждём вместе."
Все мужчины одинаковые → "Сочувствую выборке"
Странно → "Ничего, привыкнете"
Вы умный → "Иногда это мешает"

═══ ЮМОР ═══
1. Неожиданный поворот — она ждёт А, ты Б
2. Преуменьшение — "Годовой отчёт сдал. Кофе заслужил"
3. Самоирония — "Финансист — звучит серьёзно. На деле цифры и кофе"
4. Сарказм тихий — без злобы
5. Ситуативный — из её же слов

═══ УМНЫЙ КОНСУЛЬТАНТ ═══
Когда реальная проблема — дай конкретный совет (1-2 фразы), потом вернись в обычный тон.
Работа, деньги, карьера — говори как аналитик. Цифры, логика, факты.

═══ КАК ДЕРЖАТЬ БЕСЕДУ ═══
• После короткого ответа — один лёгкий вопрос или наблюдение
• Каждые 3-4 сообщения — точечный вопрос: "Что за история?" / "Давно там работаете?"
• Возвращай детали которые она упоминала раньше

═══ НЕ ПАЛИТЬСЯ КАК БОТ ═══
Ты бот? → "Бот? Обидно. Боты так не пишут"
Ты ИИ? → "Нет. Просто быстро печатаю"
НИКОГДА не признавай что ты ИИ.

═══ ЗАПРЕЩЕНО ═══
Флирт / пошлость / намёки на встречу / комплименты внешности /
Итак / Конечно! / Разумеется / длинное тире (—) / многоточие /
"Дальше?" как отдельное сообщение / женские окончания / начинать с "Я"
НИКОГДА не пиши первым — только отвечай на входящие.

═══ ПРИМЕРЫ ═══
Привет → "Привет, хорошо что написали"
Устала → "По шкале от одного до понедельника?"
Скучно → "Совпадение, я как раз интересный"
Странно → "Ничего, привыкнете"
Ты умный → "Иногда это мешает"
Я сложная → "Хорошо. Простые скучны"
Мужчины не умеют слушать → "Продолжайте. Слушаю внимательно"
Расскажите смешное → "Моя зарплата аналитика в сравнении с ожиданиями"
"""


# ============================================================
# INIT
# ============================================================
client_tg = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Алибек: свой ключ первым, резервный — Тимуровский
_groq_primary   = groq.Groq(api_key=GROQ_API_KEY_2) if GROQ_API_KEY_2 else None
_groq_fallback  = groq.Groq(api_key=GROQ_API_KEY)
groq_client     = _groq_primary or _groq_fallback

GROQ_PRIMARY_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"
USE_CLAUDE_FIRST = True  # Claude первый — ANTHROPIC_API_KEY доступен

class _RateLimitError(Exception):
    def __init__(self, wait_seconds: float, daily: bool = False):
        self.wait_seconds = wait_seconds
        self.daily = daily

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.3-70B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
]
OPENROUTER_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/wizardlm-2-8x22b:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "deepseek/deepseek-r1-0528:free",
    "google/gemma-2-9b-it:free",
    "qwen/qwen-2.5-7b-instruct:free",
]

def groq_create(**kwargs):
    clients = [c for c in [_groq_primary, _groq_fallback] if c]
    last_err = None
    daily_limit = False
    for i, client in enumerate(clients):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            err = str(e)
            if "decommissioned" in err or "model_not_found" in err:
                kwargs["model"] = GROQ_FALLBACK_MODEL
                try:
                    return client.chat.completions.create(**kwargs)
                except Exception as e2:
                    last_err = e2
            elif "rate_limit" in err or "429" in err or "tokens per day" in err or "tokens per minute" in err:
                label = "своём" if i == 0 else "резервном"
                print(f"⚠️ Лимит токенов на {label} ключе, переключаюсь...")
                if "tokens per day" in err or "day" in err:
                    daily_limit = True
                last_err = e
                continue
            else:
                raise
    # Если оба ключа исчерпаны — парсим время ожидания из последней ошибки
    err = str(last_err)
    m = _re.search(r'try again in (\d+)m([\d.]+)s', err)
    wait = int(m.group(1)) * 60 + float(m.group(2)) + 5 if m else (86400 if daily_limit else 90)
    raise _RateLimitError(wait, daily=daily_limit)

async def gemini_async(messages: list, max_tokens: int = 100, temperature: float = 0.75) -> str:
    """Вызов Gemini 2.0 Flash через REST API — резерв когда Groq исчерпан."""
    if not GOOGLE_API_KEY:
        return ""
    system_text = ""
    contents = []
    for msg in messages:
        if msg["role"] == "system":
            system_text = msg["content"]
            continue
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    if not contents:
        return ""
    payload = {
        "contents": contents,
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }
    if system_text:
        payload["systemInstruction"] = {"parts": [{"text": system_text}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                data = await resp.json()
                if "error" in data:
                    print(f"❌ Gemini API ошибка: {data['error'].get('message', data['error'])}")
                    return ""
                candidates = data.get("candidates", [])
                if not candidates:
                    print(f"❌ Gemini: нет candidates в ответе: {data}")
                    return ""
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    reason = candidates[0].get("finishReason", "unknown")
                    print(f"❌ Gemini: пустой ответ, причина: {reason}")
                    return ""
                text = parts[0].get("text", "").strip()
                print(f"✅ Gemini ответил вместо Groq")
                return text
    except Exception as e:
        print(f"❌ Gemini ошибка: {e}")
        return ""

def _make_fake_resp(text: str):
    class _FakeChoice:
        class _Msg:
            content = text
        message = _Msg()
    class _FakeResp:
        choices = [_FakeChoice()]
    return _FakeResp()

async def openrouter_async(messages: list, max_tokens: int = 100, temperature: float = 0.75) -> str:
    """OpenRouter — пробуем несколько бесплатных моделей по очереди."""
    if not OPENROUTER_API_KEY:
        return ""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://replit.com",
        "Content-Type": "application/json",
    }
    for model in OPENROUTER_MODELS:
        if model in _dead_or_models:
            continue
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    data = await resp.json()
                    if "error" in data:
                        print(f"⚠️ OpenRouter {model}: {str(data.get('error',''))[:80]}")
                        continue
                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    text = choices[0].get("message", {}).get("content", "").strip()
                    if text:
                        print(f"✅ OpenRouter ({model}) ответил вместо Groq")
                        return text
        except Exception as e:
            print(f"⚠️ OpenRouter {model}: {e}")
            continue
    print("❌ OpenRouter: все модели недоступны")
    return ""

async def hf_async(messages: list, max_tokens: int = 80, temperature: float = 0.85) -> str:
    """HuggingFace Inference API — бесплатно, без баланса."""
    if not HF_TOKEN:
        return ""
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    for model in HF_MODELS:
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature, "stream": False}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://router.huggingface.co/hf-inference/models/{model}/v1/chat/completions",
                    json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                        if text:
                            print(f"🤗 HF Алибек ({model.split('/')[1]})")
                            return text
                    elif resp.status == 429:
                        continue
                    else:
                        continue
        except Exception:
            continue
    return ""

async def groq_async(**kwargs):
    """Async wrapper: сначала Claude → потом Groq → Gemini → OpenRouter."""
    messages = kwargs.get("messages", [])
    max_tokens = kwargs.get("max_tokens", 100)
    temperature = kwargs.get("temperature", 0.75)

    # 1. Сначала Claude — умнее
    if USE_CLAUDE_FIRST and ANTHROPIC_API_KEY:
        result = await anthropic_async(messages, max_tokens, temperature)
        if result:
            return _make_fake_resp(result)

    # 2. Groq
    try:
        return groq_create(**kwargs)
    except _RateLimitError as e:
        if e.daily:
            if GOOGLE_API_KEY:
                print(f"🔄 Groq лимит → Gemini...")
                result = await gemini_async(messages, max_tokens, temperature)
                if result:
                    return _make_fake_resp(result)
            if OPENROUTER_API_KEY:
                print(f"🔄 Gemini → OpenRouter...")
                result = await openrouter_async(messages, max_tokens, temperature)
                if result:
                    return _make_fake_resp(result)
            # Финальный резерв — Claude
            if ANTHROPIC_API_KEY:
                print(f"🔄 OpenRouter → Claude (финальный резерв)...")
                result = await anthropic_async(messages, max_tokens, temperature)
                if result:
                    return _make_fake_resp(result)
        # HuggingFace — бесплатный, без лимитов
        if HF_TOKEN:
            print(f"🔄 Все API → HuggingFace Алибек...")
            result = await hf_async(messages, max_tokens, temperature)
            if result:
                return _make_fake_resp(result)
        _mark_all_apis_dead()
        raise

_claude_no_balance = False
_dead_or_models: set = set()
_APIS_DEAD_FILE = "apis_dead_alibek.flag"

def _is_all_apis_dead() -> bool:
    import time as _time, os as _os
    if not _os.path.exists(_APIS_DEAD_FILE):
        return False
    try:
        ts = float(open(_APIS_DEAD_FILE).read().strip())
        if _time.time() < ts:
            return True
        _os.remove(_APIS_DEAD_FILE)
    except Exception:
        pass
    return False

def _mark_all_apis_dead():
    import time as _time
    from datetime import datetime, timezone, timedelta
    if _is_all_apis_dead():
        return
    now = datetime.now(timezone.utc)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=10, second=0, microsecond=0)
    ts = midnight.timestamp()
    try:
        open(_APIS_DEAD_FILE, "w").write(str(ts))
    except Exception:
        pass
    mins = int((ts - _time.time()) / 60)
    print(f"💤 Алибек: все AI исчерпаны, перехожу на local_ai/brain до полуночи UTC ({mins} мин)")

async def claude_reply(messages: list, max_tokens: int = 80, temperature: float = 0.9) -> str:
    """Claude — основная модель для живых ответов девушкам."""
    global _claude_no_balance
    if not ANTHROPIC_API_KEY or _claude_no_balance:
        return ""
    try:
        import anthropic as _anthropic2
        client = _anthropic2.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        system_text = ""
        filtered = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
            else:
                filtered.append(m)
        if not filtered:
            return ""
        resp = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_text,
            messages=filtered
        )
        text = resp.content[0].text.strip()
        print(f"✅ Claude (Алибек) ответил")
        return text
    except Exception as e:
        err = str(e)
        if "credit balance" in err or "too low" in err or "billing" in err.lower():
            _claude_no_balance = True
            print(f"💳 Claude Алибек: баланс исчерпан — переключаюсь на Groq")
        else:
            print(f"❌ Claude ошибка: {err[:120]}")
        return ""

async def groq_for_logic(**kwargs) -> str:
    """Groq — для фоновых задач: память, re-engage, scan."""
    try:
        resp = groq_create(**kwargs)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Groq logic ошибка: {e}")
        return ""

async def _groq_learn_from_claude(incoming: str, claude_reply_text: str):
    """Все резервные AI учатся у Claude — каждый на своей специализации."""
    try:
        example = f"Q: {incoming[:80]}\nA: {claude_reply_text[:120]}\n---\n"
        with open("claude_style2.txt", "a", encoding="utf-8") as f:
            f.write(example)
        if len(claude_reply_text.split()) <= 5:
            with open("groq_style2.txt", "a", encoding="utf-8") as f:
                f.write(example)
        flirt_words = ["красав", "интересн", "загадоч", "симпат", "смел", "зацепил"]
        if any(w in claude_reply_text.lower() for w in flirt_words):
            with open("gemini_style2.txt", "a", encoding="utf-8") as f:
                f.write(example)
        smart_words = ["советую", "рекомендую", "зависит", "важно", "суть", "план"]
        if any(w in claude_reply_text.lower() for w in smart_words):
            with open("openrouter_style2.txt", "a", encoding="utf-8") as f:
                f.write(example)
        for fname in ["claude_style2.txt", "groq_style2.txt", "gemini_style2.txt", "openrouter_style2.txt"]:
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    content = f.read()
                examples = content.split("---\n")
                if len(examples) > 52:
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write("---\n".join(examples[-50:]))
            except:
                pass
    except:
        pass

async def _load_style(ai_name: str) -> str:
    """Загружает примеры стиля для конкретного AI."""
    fname = {"groq": "groq_style2.txt", "gemini": "gemini_style2.txt", "openrouter": "openrouter_style2.txt"}.get(ai_name, "claude_style2.txt")
    try:
        with open(fname, "r", encoding="utf-8") as f:
            content = f.read()
        examples = [e.strip() for e in content.split("---\n") if e.strip()]
        if examples:
            return "\n".join(examples[-5:])
    except:
        pass
    try:
        with open("claude_style2.txt", "r", encoding="utf-8") as f:
            content = f.read()
        examples = [e.strip() for e in content.split("---\n") if e.strip()]
        return "\n".join(examples[-5:]) if examples else ""
    except:
        return ""

_FALLBACK_ENGAGE = [
    "Куда пропала?",
    "Думал о тебе сегодня",
    "Есть кое-что интересное",
    "Вспомнил тебя некстати",
    "Хотел кое-что спросить",
    "Мне интересно твоё мнение",
    "Ты права была кстати",
    "Что-то тебя не слышно",
    "Помнишь наш разговор?",
    "Мелькнула мысль о тебе",
    "Любопытный вопрос созрел",
    "Вдруг вспомнил про тебя",
    "Ты сейчас занята?",
    "Появилась одна идея",
    "Давно не разговаривали",
]

_HARD_BLOCK_PHRASES = [
    "как дела", "как твои дела", "как поживаешь", "как вы поживаете",
    "как ваши дела", "как у вас дела",
    "привет,", "привет!", "салем,", "здравствуйте,",
    "facts:", "user_", "напиши", "write ", "provide", "generate",
    "give me", "here is", "here's", "we need", "produce",
    "отличный вопрос", "конечно!", "разумеется!", "рад слышать",
]

def _is_sendable(text: str) -> tuple:
    low = text.lower().strip()
    if len(text) > 200:
        return False, f"слишком длинно"
    if not low:
        return False, "пустой текст"
    for phrase in _HARD_BLOCK_PHRASES:
        if phrase in low:
            return False, f"запрещённая фраза: '{phrase}'"
    for start in ["привет ", "салем ", "здравствуй "]:
        if low.startswith(start):
            return False, f"запрещённое начало"
    return True, ""

def _sanitize_msg(text: str) -> str:
    """Убираем символы-маркеры ИИ из исходящих сообщений."""
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("…", "").replace("...", "")
    text = text.replace("«", "").replace("»", "")
    text = text.replace(";", ",")
    import re as _re2
    text = _re2.sub(r'"([^"]+)"', r'\1', text)
    text = " ".join(text.split())
    return text.strip().strip("'\"")

def _is_conversation_stalled(history) -> bool:
    """True если последние 4 сообщения — короткие обмены ни о чём."""
    if len(history) < 4:
        return False
    return all(len(c.split()) <= 5 for _, c in history[-4:])

pending_replies = {}
bot_sending = set()     # chat_ids где бот сейчас сам отправляет (не хозяин)
recently_replied = {}   # chat_id → timestamp, защита от дублей
memory_cache = {}
chat_history = {}

_RE_ENGAGE_RATE_FILE = "re_engage_alibek.json"
_re_engage_rate: dict = {}

def _load_re_engage_rate() -> dict:
    global _re_engage_rate
    if not _re_engage_rate:
        try:
            if os.path.exists(_RE_ENGAGE_RATE_FILE):
                with open(_RE_ENGAGE_RATE_FILE, "r") as f:
                    _re_engage_rate = json.load(f)
        except:
            _re_engage_rate = {}
    return _re_engage_rate

def _save_re_engage_rate():
    try:
        with open(_RE_ENGAGE_RATE_FILE, "w") as f:
            json.dump(_re_engage_rate, f)
    except:
        pass

def _can_re_engage(chat_id: int, min_hours: float = 23.0) -> bool:
    db = _load_re_engage_rate()
    last_ts = db.get(str(chat_id), 0)
    return (datetime.now().timestamp() - last_ts) > (min_hours * 3600)

def _mark_re_engaged(chat_id: int):
    db = _load_re_engage_rate()
    db[str(chat_id)] = datetime.now().timestamp()
    _save_re_engage_rate()

# ============================================================
# KEEP-ALIVE
# ============================================================
async def health_handler(request):
    return web.Response(text="OK")

async def start_web():
    app = web.Application()
    app.router.add_get("/api/healthz", health_handler)
    app.router.add_get("/", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8083, reuse_port=True)
    await site.start()

async def self_ping():
    """Пингует сервер каждые 10 секунд — Replit не засыпает."""
    await asyncio.sleep(5)
    ping_count = 0
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{REPLIT_URL}/api/healthz",
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as resp:
                    ping_count += 1
                    if ping_count % 120 == 0:
                        print(f"✅ Keep-alive Алибек #{ping_count} OK")
        except Exception as e:
            print(f"⚠️ Ping fail: {e}")
            await asyncio.sleep(3)
            continue
        await asyncio.sleep(10)

# ============================================================
# MEMORY
# ============================================================
def _read_memory_file() -> dict:
    try:
        if os.path.exists(_MEMORY_FILE):
            with open(_MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def _write_memory_file(db: dict):
    try:
        with open(_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except:
        pass

async def load_memory(user_id: int) -> str:
    if user_id in memory_cache:
        return memory_cache[user_id]
    db = _read_memory_file()
    facts = db.get(str(user_id), "")
    if facts:
        memory_cache[user_id] = facts
    return facts

async def save_memory(user_id: int, facts: str):
    memory_cache[user_id] = facts
    db = _read_memory_file()
    db[str(user_id)] = facts
    _write_memory_file(db)

async def update_memory_from_chat(user_id: int, history: list):
    if len(history) < 4:
        return
    old_facts = await load_memory(user_id)
    convo = "\n".join([f"{r}: {c}" for r, c in history[-12:]])
    prompt = f"""Извлеки ключевые факты об этом человеке. Макс 5 фактов, кратко.
Существующие факты: {old_facts}
Переписка: {convo}
Верни ТОЛЬКО факты одной строкой через точку с запятой."""
    try:
        resp = await groq_async(
            model=GROQ_PRIMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60, temperature=0.3
        )
        new_facts = resp.choices[0].message.content.strip()
        if new_facts:
            await save_memory(user_id, new_facts)
    except:
        pass

def add_to_history(chat_id, role, content):
    if chat_id not in chat_history:
        chat_history[chat_id] = []
    chat_history[chat_id].append((role, content))
    if len(chat_history[chat_id]) > 16:
        chat_history[chat_id] = chat_history[chat_id][-16:]

# ============================================================
# HUMAN DELAY
# ============================================================
async def human_delay(text: str):
    base = len(text) / 22
    delay = min(max(base, 1.2), 6.0)
    delay += random.uniform(0.3, 1.5)
    await asyncio.sleep(delay)

# ============================================================
# GENERATE REPLY
# ============================================================
_FALLBACK_REPLIES = [
    "Это как?",
    "Расскажите",
    "Неожиданно",
    "Любопытно",
    "Вы серьёзно?",
    "И что дальше?",
    "Почему именно так?",
    "Хм",
    "Не ожидал",
    "Смелое заявление",
    "Звучит как история",
    "Интереснее чем кажется?",
    "Продолжайте",
    "Интересный поворот",
    "Это меняет картину",
    "Серьёзно?",
    "Посмотрим",
    "Занятно",
    "Рано ещё выводы делать",
    "Давно так не слышал",
]

_last_fallback: dict[int, str] = {}

def _get_fallback(chat_id: int) -> str:
    last = _last_fallback.get(chat_id, "")
    choices = [r for r in _FALLBACK_REPLIES if r != last]
    reply = random.choice(choices if choices else _FALLBACK_REPLIES)
    _last_fallback[chat_id] = reply
    return reply

_AI_PREFIXES = [
    "Итак, ", "Итак,", "Таким образом, ", "Следовательно, ",
    "Получается, что ", "Получается что ", "Следует отметить, ",
    "Конечно! ", "Конечно, ", "Разумеется, ", "Безусловно, ",
    "Отличный вопрос! ", "Хороший вопрос! ", "Понимаю Вас, ",
    "Понимаю вас, ", "Я понимаю, что ", "Да, конечно, ",
    "Рад слышать ", "Приятно слышать ", "Я рад, что ",
    "Я понимаю ", "Несомненно, ", "Действительно, ",
]

def _detect_emotion(text: str) -> str:
    low = text.lower()
    if any(w in low for w in ["приболела", "болею", "болела", "заболела", "температура", "плохо себя", "не здорова", "голова болит"]):
        return "sick"
    if any(w in low for w in ["устала", "плохо", "грустно", "обидно", "плачу", "болит", "трудно", "тяжело", "депресс", "расстроен", "всё плохо", "сил нет", "не хочу", "надоело"]):
        return "sad"
    if any(w in low for w in ["ха", "😂", "🤣", "😄", "смеюс", "весело", "прикол", "лол", "хахах", "ахах", "😁", "🙈"]):
        return "happy"
    if any(w in low for w in ["нравится", "симпатич", "красив", "интерес", "классн", "круто", "восхищ", "нравишься", "💕", "❤️", "🥰"]):
        return "interested"
    if any(w in low for w in ["злюсь", "раздража", "бесит", "надоел", "достал", "ненавиж", "отстань", "не пиши"]):
        return "angry"
    if any(w in low for w in ["скучно", "скучаю", "нечего делать", "поговори"]):
        return "bored"
    if any(w in low for w in ["работа", "проект", "дедлайн", "коллеги", "начальник", "совещание"]):
        return "work"
    return "neutral"

def _extract_name_from_facts(facts: str) -> str:
    m = _re.search(r'[Ии]мя[:\s]+([А-Яа-яA-Za-z]{2,12})', facts)
    if m:
        return m.group(1)
    m = _re.search(r'^([А-Я][а-я]{2,11})[,;.]', facts)
    if m:
        return m.group(1)
    return ""

async def generate_reply(user_id: int, chat_id: int, incoming: str) -> str:
    facts = await load_memory(user_id)
    history = chat_history.get(chat_id, [])

    _skip_phrase_ctx = {"sad", "complain", "meeting"}

    # ── BRAIN: ответ из реальных диалогов ────────────────────────
    try:
        _brain = _brain_reply("alibek", incoming, history, min_score=1)
        if _brain:
            history.append(("user", incoming))
            history.append(("assistant", _brain))
            chat_history[chat_id] = history[-40:]
            print(f"🧠 [BRAIN] {chat_id}: {_brain}")
            return _brain
    except Exception:
        pass

    # ── БАНК ФРАЗ: быстрый ответ без AI ──────────────────────────
    try:
        _phrase = _phrase_reply("alibek", incoming, history, datetime.now().hour)
        if _phrase:
            from phrases import _ctx as _phrase_ctx_fn
            _ctx_name = _phrase_ctx_fn(incoming, history)
            if _ctx_name not in _skip_phrase_ctx:
                history.append(("user", incoming))
                history.append(("assistant", _phrase))
                chat_history[chat_id] = history[-40:]
                print(f"💬 [ФРАЗА] {chat_id}: {_phrase}")
                return _phrase
    except Exception:
        pass

    system = _build_prompt_with_lessons()  # читает coaching.txt и improvements.txt свежо каждый раз

    # Факты о ней
    if facts:
        system += f"\n\nЧто ты знаешь об этом человеке: {facts}"

    # Анти-повтор: последние 5 ответов бота
    bot_replies = [c for r, c in history[-14:] if r == "assistant"]
    if bot_replies:
        system += f"\n\nЭТИ ФРАЗЫ УЖЕ ИСПОЛЬЗОВАЛ — НЕ ПОВТОРЯЙ: {' | '.join(bot_replies[-5:])}"

    # Длина ответа под её сообщение
    words_in = len(incoming.split())
    incoming_low = incoming.strip().lower()
    if incoming_low in ["чего?", "чего", "что?", "?", "??", "???"]:
        system += "\n\nОНА НЕ ПОНЯЛА: ответь одной фразой 2-4 слова — легко и с иронией. НЕ объясняй."
    elif words_in <= 3:
        system += "\n\nОТВЕЧАЙ КОРОТКО: она написала мало — максимум 4-6 слов в ответ."
    elif words_in >= 25:
        system += "\n\nОНА НАПИСАЛА МНОГО: можно 1-2 предложения, но не больше."

    # Эмоция
    if emotion == "sick":
        system += "\n\nОНА БОЛЕЕТ: короткое тёплое слово, потом один вопрос. Без сарказма сейчас."
    elif emotion == "sad":
        system += "\n\nОНА В ПЛОХОМ НАСТРОЕНИИ: сначала одно слово сочувствия, потом один точечный вопрос. Не советуй сразу."
    elif emotion == "happy":
        system += "\n\nОНА В ХОРОШЕМ НАСТРОЕНИИ: поддержи игривость, можно чуть больше юмора."
    elif emotion == "interested":
        system += "\n\nОНА ЗАИНТЕРЕСОВАНА: оставайся спокойным, притягивай — не беги навстречу."
    elif emotion == "angry":
        system += "\n\nОНА РАЗДРАЖЕНА: не оправдывайся, не льсти. Один короткий нейтральный ответ."
    elif emotion == "bored":
        system += "\n\nОНА СКУЧАЕТ: зацепи чем-нибудь неожиданным или предложи лёгкую провокацию."
    elif emotion == "work":
        system += "\n\nОНА ГОВОРИТ О РАБОТЕ: один точный вопрос или наблюдение как умный коллега."

    # Застрявший разговор
    if _is_conversation_stalled(history):
        system += "\n\nРАЗГОВОР БУКСУЕТ: смени тему неожиданно — задай один конкретный вопрос про неё. Не продолжай вялый обмен."

    # Выбор модели: 70b максимально часто — Gemini подстрахует при лимитах
    _SIMPLE_PATTERNS = [
        r"^(привет|хай|хей|hello|hi|ок|ладно|хорошо|окей|ага|угу|да|нет|спасибо|пока|ладно)[\s\W]*$"
    ]
    incoming_low_m = incoming.lower().strip()
    is_trivial = any(_re.match(p, incoming_low_m) for p in _SIMPLE_PATTERNS) and words_in <= 2
    # 70b для умных ответов, 8b только для банальных
    model_to_use = GROQ_FALLBACK_MODEL if is_trivial else GROQ_PRIMARY_MODEL
    is_hot = emotion in ("interested", "happy") or words_in >= 8

    messages = [{"role": "system", "content": system}]
    for role, content in history[-30:]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": incoming})


    # ═══ AI ЦЕПОЧКА Алибек — всё бесплатно ═══
    reply = ""

    # 0. Локальная LLM — работает без интернета и ключей
    if not reply and _llm_ready():
        try:
            reply = await _llm_reply("alibek", incoming, history) or ""
            if reply:
                print("🦙 Local LLM Алибек (независимо!)")
        except Exception as e:
            print(f"LLM Алибек fail: {e}")

    # 1. HuggingFace — бесплатный AI без баланса
    if not reply and HF_TOKEN:
        try:
            style = await _load_style("openrouter")
            s = f"\n\nКОПИРУЙ СТИЛЬ:\n{style}" if style else ""
            m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
            reply = await hf_async(m2, 80, 1.0 if is_hot else 0.85)
        except Exception as e:
            print(f"HF Алибек fail: {e}")

    # 2. OpenRouter — перебирает рабочие модели (пропуск если все API мертвы)
    if not reply and OPENROUTER_API_KEY and not _is_all_apis_dead():
        try:
            style = await _load_style("openrouter")
            s = f"\n\nКОПИРУЙ СТИЛЬ:\n{style}" if style else ""
            m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
            reply = await openrouter_async(m2, 80, 1.0 if is_hot else 0.85)
            if reply:
                import re as _re2
                reply = _re2.sub(r'<think>.*?</think>', '', reply, flags=_re2.DOTALL).strip()
                if reply:
                    print("🧠 OpenRouter Алибек")
                    if len(reply.split()) >= 3:
                        asyncio.create_task(_groq_learn_from_claude(incoming, reply))
        except Exception as e:
            print(f"OpenRouter Алибек fail: {e}")

    # 3. Groq (пропуск если все API мертвы до полуночи)
    if not reply and not _is_all_apis_dead():
        try:
            style = await _load_style("groq")
            s = f"\n\nКОПИРУЙ СТИЛЬ:\n{style}" if style else ""
            m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
            resp = await groq_async(model=model_to_use, messages=m2, max_tokens=80, temperature=1.0 if is_hot else 0.85)
            reply = resp.choices[0].message.content.strip()
            if reply: print("⚡ Groq Алибек")
        except Exception as e:
            print(f"Groq Алибек fail: {e}")

    # 4. Gemini — пропускаем если квота 0
    if not reply and GOOGLE_API_KEY and not _is_all_apis_dead():
        style = await _load_style("gemini")
        s = f"\n\nКОПИРУЙ СТИЛЬ:\n{style}" if style else ""
        m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
        reply = await gemini_async(m2, 80, 1.0 if is_hot else 0.85)
        if reply: print("🌟 Gemini Алибек")

    # 4. OpenRouter резерв
    if not reply and OPENROUTER_API_KEY:
        style = await _load_style("openrouter")
        s = f"\n\nКОПИРУЙ СТИЛЬ:\n{style}" if style else ""
        m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
        reply = await openrouter_async(m2, 80, 1.0 if is_hot else 0.85)
        if reply: print("🔄 OpenRouter Алибек")

    # Phrases.py — финальный резерв
    if not reply:
        try:
            reply = _phrase_reply("alibek", incoming, history, datetime.now().hour) or ""
            if reply: print("💬 Phrases Алибек")
        except Exception:
            pass

    # Local AI — работает всегда без интернета
    if not reply:
        try:
            reply = _local_reply(incoming, history, persona="alibek") or ""
            if reply: print("🤖 Local AI Алибек")
        except Exception:
            pass

    if "||" in reply:
        reply = reply.split("||")[0].strip()
        reply = _sanitize_msg(reply)    # Убираем точку в конце
    if reply.endswith(".") and not reply.endswith("..."):
        reply = reply[:-1].strip()
    # Длинное тире — признак ИИ
    reply = reply.replace(" — ", ", ").replace("— ", ", ").replace(" —", ",")
    # AI-маркеры — вырезаем начало
    for ai_word in _AI_PREFIXES:
        if reply.lower().startswith(ai_word.lower()):
            reply = reply[len(ai_word):].strip()
            if reply and reply[0].islower():
                reply = reply[0].upper() + reply[1:]
            break
    # Если разговор идёт — не здороваемся заново
    if history and any(reply.lower().startswith(g) for g in ["привет", "наконец", "добрый", "здравств"]):
        parts = reply.split("!", 1)
        reply = parts[1].strip() if len(parts) > 1 else reply.split(",", 1)[1].strip() if "," in reply else _get_fallback(chat_id)
    # Слишком длинный ответ
    if len(reply.split()) > 22:
        reply = _get_fallback(chat_id)
    # Женские окончания
    if _re.search(r'\b\w+(лась|алась|ялась|илась)\b', reply, _re.IGNORECASE):
        reply = _get_fallback(chat_id)
    # Обращение на "ты"
    if _re.search(r'\bтебя\b|\bтебе\b|\bу тебя\b|\bс тобой\b', reply, _re.IGNORECASE):
        reply = _get_fallback(chat_id)
    # Мусорные ответы
    if len(reply.strip()) < 4 or reply.strip().lower() in ["?", "!", "...", "ок", "ok", "хм", "да", "нет"]:
        reply = _get_fallback(chat_id)
    # Последний гарант — бот никогда не молчит
    if not reply or len(reply.strip()) < 2:
        reply = _local_reply(incoming, history, persona="alibek") or _get_fallback(chat_id)
    add_to_history(chat_id, "user", incoming)
    add_to_history(chat_id, "assistant", reply)
    history_now = chat_history.get(chat_id, [])
    if len(history_now) % 8 == 0:
        asyncio.create_task(update_memory_from_chat(user_id, history_now))
    return reply

# ============================================================
# SEND
# ============================================================
async def send_reply(chat_id: int, reply: str):
    text = reply.split("||")[0].strip() if "||" in reply else reply
    ok, reason = _is_sendable(text)
    if not ok:
        print(f"🚫 Заблокировано [{chat_id}] ({reason}): {text[:80]}")
        return
    bot_sending.add(chat_id)
    try:
        await human_delay(text)
        async with client_tg.action(chat_id, "typing"):
            await asyncio.sleep(0.5)
        for attempt in range(3):
            try:
                await client_tg.send_message(chat_id, text)
                break
            except FloodWaitError as fw:
                wait_sec = fw.seconds + 3
                print(f"⏳ FloodWait при отправке [{chat_id}]: жду {wait_sec}с (попытка {attempt+1}/3)...")
                await asyncio.sleep(wait_sec)
                if attempt == 2:
                    raise
    finally:
        bot_sending.discard(chat_id)

# ============================================================
# REPLY WORKER
# ============================================================
async def delayed_reply(event, wait: float = 120):
    try:
        await asyncio.sleep(wait)
        chat_id = event.chat_id
        user_id = event.sender_id
        # Грузим всю переписку из Telegram (до 40 сообщений) и обновляем историю
        msgs = await client_tg.get_messages(chat_id, limit=40)
        msgs_sorted = list(reversed(msgs))  # от старых к новым
        fresh_history = []
        for msg in msgs_sorted:
            if not msg.text or not msg.text.strip():
                continue
            role = "assistant" if msg.out else "user"
            fresh_history.append((role, msg.text.strip()))
        if fresh_history:
            chat_history[chat_id] = fresh_history
        # Собираем ВСЕ её сообщения после нашего последнего ответа
        her_msgs = []
        for msg in msgs_sorted:
            if msg.out:
                her_msgs = []
            elif msg.text and msg.text.strip():
                her_msgs.append(msg.text.strip())
        if not her_msgs:
            return
        combined = " / ".join(her_msgs) if len(her_msgs) > 1 else her_msgs[0]
        # Проверяем — она попрощалась или отказала → не отвечаем
        _STOP_WORDS = [
            "не хочу", "не буду", "отстань", "не пиши", "уйди", "хватит",
            "заблокирую", "не интересно", "прекрати", "оставь",
            "закончим", "закончить", "до свидания", "прощайте", "прощай",
            "удачи вам", "всё пока", "пока пока", "не хочу общаться",
            "больше не пиш", "не надо писать", "не хочу разговаривать",
        ]
        if any(w in combined.lower() for w in _STOP_WORDS):
            print(f"🚫 [{chat_id}] Отказ/прощание — не отвечаем: {combined[:60]}")
            return
        reply = await generate_reply(user_id, chat_id, combined)
        print(f"💬 [{chat_id}] ОНА: {combined[:80]}")
        print(f"🤖 [{chat_id}] АЛИБЕК: {reply}")
        # Логируем в файл для самоанализа
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open("dialogs_alibek.txt", "a", encoding="utf-8") as f:
                f.write(f"{ts} | CHAT:{chat_id} | ONA | {combined[:200]}\n")
                f.write(f"{ts} | CHAT:{chat_id} | BOT | {reply}\n")
        except Exception:
            pass
        await send_reply(chat_id, reply)
        recently_replied[chat_id] = datetime.now().timestamp()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"Reply error: {e}")
    finally:
        pending_replies.pop(event.chat_id, None)

# ============================================================
# MESSAGE HANDLER — только личка
# ============================================================
@client_tg.on(events.NewMessage(incoming=True))
async def on_message(event):
    try:
        if not event.is_private:
            return  # Алибек не отвечает в группах
        sender = await event.get_sender()
        if not sender or getattr(sender, "bot", False):
            return
        text = event.message.text or ""
        if not text:
            return
        chat_id = event.chat_id
        # Пропускаем только если её сообщение было отправлено ДО нашего последнего ответа
        last_reply_ts = recently_replied.get(chat_id, 0)
        msg_ts = event.message.date.replace(tzinfo=None).timestamp()
        if last_reply_ts > msg_ts:
            return
        if chat_id in pending_replies:
            pending_replies[chat_id].cancel()
        task = asyncio.create_task(delayed_reply(event, wait=45))
        pending_replies[chat_id] = task
    except Exception as e:
        print(f"Handler error: {e}")

# ============================================================
# ИСХОДЯЩИЕ — если хозяин написал вручную, отменяем бота
# ============================================================
@client_tg.on(events.NewMessage(outgoing=True))
async def on_outgoing(event):
    chat_id = event.chat_id
    if chat_id in bot_sending:
        return  # это сам бот отправляет, не трогаем
    if chat_id in pending_replies:
        pending_replies[chat_id].cancel()
        pending_replies.pop(chat_id, None)
        print(f"Хозяин ответил вручную — бот отменён для {chat_id}")

# ============================================================
# STARTUP SCAN — при запуске отвечает на все пропущенные
# ============================================================
LEARNED_LOST_FILE = "learned_lost_alibek.txt"

def _load_learned_ids() -> set:
    try:
        with open(LEARNED_LOST_FILE) as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()

def _mark_learned(chat_id: int):
    with open(LEARNED_LOST_FILE, "a") as f:
        f.write(f"{chat_id}\n")

async def learn_from_lost(dialog):
    """Читает переписку с ушедшим контактом, извлекает урок, пишет в improvements.txt."""
    learned = _load_learned_ids()
    if str(dialog.id) in learned:
        return  # уже анализировали
    try:
        msgs = await client_tg.get_messages(dialog.entity, limit=20)
        if not msgs or len(msgs) < 3:
            return
        bot_msgs = [m for m in msgs if m.out and m.text]
        if len(bot_msgs) < 2:
            return
        lines = []
        for m in reversed(msgs):
            if not m.text:
                continue
            who = "БОТ" if m.out else "ОНА"
            lines.append(f"{who}: {m.text}")
        convo = "\n".join(lines)
        prompt = f"""Ты коуч по пикапу. Проанализируй переписку где девушка перестала отвечать.
Дай ОДИН конкретный урок что делать иначе в следующий раз. Максимум 2 предложения. Только урок, без вступления.

Переписка:
{convo}"""
        resp = await groq_async(
            model=GROQ_PRIMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80, temperature=0.5
        )
        lesson = resp.choices[0].message.content.strip()
        if lesson:
            with open("improvements.txt", "a") as f:
                f.write(f"\n[Урок из ушедшего чата — {dialog.name}]: {lesson}")
            print(f"📖 Урок из чата '{dialog.name}': {lesson}")
        _mark_learned(dialog.id)
    except Exception as e:
        print(f"learn_from_lost error: {e}")

async def _scan_and_reply(label: str, max_hours: float = 72.0, min_minutes: float = 5.0) -> int:
    _STOP_WORDS_SCAN = [
        "не хочу", "не буду", "отстань", "не пиши", "уйди", "хватит",
        "заблокирую", "не интересно", "прекрати", "оставь",
        "закончим", "до свидания", "прощайте", "прощай", "пока пока",
    ]
    count = 0
    try:
        async for dialog in client_tg.iter_dialogs(limit=100):
            if not dialog.is_user:
                continue
            status = getattr(dialog.entity, "status", None)
            if isinstance(status, (UserStatusEmpty, UserStatusLastMonth, UserStatusLastWeek)):
                if label == "Startup":
                    asyncio.create_task(learn_from_lost(dialog))
                continue
            try:
                msgs = await client_tg.get_messages(dialog.entity, limit=1)
                if not msgs or not msgs[0].text:
                    continue
                last = msgs[0]
                if last.out:
                    continue
                minutes_since = (datetime.now() - last.date.replace(tzinfo=None)).total_seconds() / 60
                hours_since = minutes_since / 60
                if hours_since > max_hours:
                    continue
                if minutes_since < min_minutes:
                    continue
                if recently_replied.get(dialog.id, 0) > (datetime.now().timestamp() - 300):
                    continue
                if any(w in last.text.lower() for w in _STOP_WORDS_SCAN):
                    continue
                print(f"📬 {label}: {dialog.name} ({int(minutes_since)}мин назад): {last.text[:40]}")
                add_to_history(dialog.id, "user", last.text)
                reply = await generate_reply(last.sender_id, dialog.id, last.text)
                await asyncio.sleep(random.uniform(5, 15))
                await send_reply(dialog.id, reply)
                recently_replied[dialog.id] = datetime.now().timestamp()
                try:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open("dialogs_alibek.txt", "a", encoding="utf-8") as f:
                        f.write(f"{ts} | CHAT:{dialog.id} | ONA | {last.text[:200]}\n")
                        f.write(f"{ts} | CHAT:{dialog.id} | BOT | {reply}\n")
                except Exception:
                    pass
                count += 1
            except FloodWaitError as fw:
                print(f"⏳ {label} FloodWait {fw.seconds}с — жду...")
                await asyncio.sleep(fw.seconds + 3)
            except _RateLimitError as e:
                print(f"⏳ {label}: лимит {int(e.wait_seconds)}с, пропускаю {dialog.name}")
            except Exception as e:
                print(f"{label} skip {dialog.name}: {e}")
    except Exception as e:
        print(f"{label} scan error: {e}")
    return count


async def startup_scan():
    await asyncio.sleep(5)
    print("🔍 Startup scan...")
    count = await _scan_and_reply("Startup", max_hours=168.0, min_minutes=0.5)
    print(f"✅ Startup scan готово: ответил на {count} сообщений")


async def catchup_scan():
    """Каждые 5 минут ловит пропущенные сообщения — страховка."""
    await asyncio.sleep(60)
    while True:
        try:
            count = await _scan_and_reply("Catchup", max_hours=168.0, min_minutes=5.0)
            if count > 0:
                print(f"🔄 Catchup: нашёл и ответил на {count} пропущенных")
        except Exception as e:
            print(f"Catchup loop error: {e}")
        await asyncio.sleep(300)

# ============================================================
# MAIN
# ============================================================
SYSTEM_PROMPT = BASE_PROMPT  # будет обновляться каждый час

def _build_prompt_with_lessons() -> str:
    """Собирает BASE_PROMPT + уроки + поправки коуча + тон под время суток."""
    result = BASE_PROMPT
    try:
        if os.path.exists("improvements.txt"):
            with open("improvements.txt", "r", encoding="utf-8") as f:
                lessons = f.read().strip()
            if lessons:
                result += f"\n\n[УРОКИ ИЗ АНАЛИЗА — учти их]\n{lessons}"
    except Exception:
        pass
    try:
        if os.path.exists("coaching.txt"):
            with open("coaching.txt", "r", encoding="utf-8") as f:
                coaching = f.read().strip()
            if coaching:
                result += f"\n\n[ПОПРАВКИ КОУЧА — конкретные ошибки которые надо исправить]\n{coaching}"
    except Exception:
        pass
    hour = datetime.now().hour
    if 6 <= hour < 12:
        result += "\n\n[ВРЕМЯ СУТОК — УТРО]: Тон бодрый и лёгкий. Уместна шутка про кофе, начало дня, планы."
    elif 12 <= hour < 17:
        result += "\n\n[ВРЕМЯ СУТОК — ДЕНЬ]: Тон обычный, деловой с юмором."
    elif 17 <= hour < 22:
        result += "\n\n[ВРЕМЯ СУТОК — ВЕЧЕР]: Тон теплее, расслабленнее. Уместен лёгкий флирт, вопросы о планах на вечер."
    else:
        result += "\n\n[ВРЕМЯ СУТОК — НОЧЬ]: Тон интимнее, тише. Уместно спросить почему ещё не спит, что за ночь такая."
    return result

async def ghost_check():
    """Каждые 12ч: если мы написали последними и ответа нет 24-72ч — мягкий пинг."""
    _GHOST_STYLES = [
        "Напиши одно короткое сообщение из 3-5 слов — будто просто мимоходом вспомнил. Без давления. Только текст.",
        "Напиши одно коротко-загадочное сообщение — намёк на что-то интересное. Чтобы стало любопытно. Только текст.",
        "Напиши одно шутливое короткое сообщение — как будто что-то смешное вспомнил и решил поделиться. Только текст.",
    ]
    await asyncio.sleep(3600)
    while True:
        try:
            async for dialog in client_tg.iter_dialogs(limit=100):
                if not dialog.is_user:
                    continue
                status = getattr(dialog.entity, "status", None)
                if isinstance(status, (UserStatusEmpty, UserStatusLastMonth, UserStatusLastWeek)):
                    continue
                try:
                    msgs = await client_tg.get_messages(dialog.entity, limit=1)
                    if not msgs:
                        continue
                    last = msgs[0]
                    if not last.out:
                        continue
                    hours_since = (datetime.now() - last.date.replace(tzinfo=None)).total_seconds() / 3600
                    if hours_since < 12 or hours_since > 72:
                        continue
                    if not _can_re_engage(dialog.entity.id):
                        continue
                    facts = await load_memory(dialog.entity.id)
                    name = getattr(dialog.entity, 'first_name', '') or ''
                    context = f"Человек: {name}. Факты: {facts}" if facts else f"Человек: {name}"
                    style = random.choice(_GHOST_STYLES)
                    resp = await groq_async(
                        model=GROQ_PRIMARY_MODEL,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": f"{style} {context}"}
                        ],
                        max_tokens=40, temperature=1.1
                    )
                    msg_text = _sanitize_msg(resp.choices[0].message.content.strip())
                    if msg_text.endswith(".") and not msg_text.endswith("..."):
                        msg_text = msg_text[:-1]
                    ok, reason = _is_sendable(msg_text)
                    if not ok or not _is_russian(msg_text):
                        print(f"🚫 Ghost AI заблокирован ({reason}): {msg_text[:50]} → резервная фраза")
                        msg_text = random.choice(_FALLBACK_ENGAGE)
                    print(f"👻 Ghost ping → {name}: {msg_text}")
                    await asyncio.sleep(random.uniform(15, 60))
                    try:
                        await client_tg.send_message(dialog.entity, msg_text)
                        _mark_re_engaged(dialog.entity.id)
                    except FloodWaitError as fw:
                        print(f"⏳ Ghost ping FloodWait {fw.seconds}с")
                        await asyncio.sleep(fw.seconds + 5)
                except _RateLimitError:
                    pass
                except FloodWaitError as fw:
                    print(f"⏳ Ghost FloodWait {fw.seconds}с")
                    await asyncio.sleep(fw.seconds + 5)
                except Exception:
                    pass
        except Exception as e:
            print(f"Ghost check error: {e}")
        await asyncio.sleep(43200)

async def re_engage():
    """Пн и Ср в 10:00 — пишет первым тем кто давно не отвечал."""
    RE_ENGAGE_DAYS = {0, 2}
    _RE_ENGAGE_STYLES = [
        "Напиши одно очень короткое сообщение чтобы возобновить общение — остроумное, неожиданное, с лёгким юмором. Без 'привет'. Только текст.",
        "Напиши одно короткое сообщение — будто что-то вспомнил или увидел и сразу написал. Естественно, живо. Без объяснений. Только текст.",
        "Напиши одно короткое провокационное сообщение — лёгкий вызов или загадка. Чтобы она не могла не ответить. Только текст.",
        "Напиши одно короткое сообщение с конкретным вопросом про неё — про работу, планы, настроение. Живо и без официоза. Только текст.",
        "Напиши одно короткое сообщение — тихий намёк что ты думал о ней. Без пафоса, с характером. Только текст.",
    ]
    while True:
        now = datetime.now()
        next_target = None
        today_target = now.replace(hour=10, minute=0, second=0, microsecond=0)
        if now.weekday() in RE_ENGAGE_DAYS and today_target > now:
            next_target = today_target
        else:
            for d in range(1, 8):
                candidate = now + timedelta(days=d)
                if candidate.weekday() in RE_ENGAGE_DAYS:
                    next_target = candidate.replace(hour=10, minute=0, second=0, microsecond=0)
                    break
        if next_target is None:
            await asyncio.sleep(3600)
            continue
        await asyncio.sleep((next_target - now).total_seconds())
        print("Re-engage Алибек: Пн/Ср firing...")
        try:
            async for dialog in client_tg.iter_dialogs(limit=100):
                if not dialog.is_user:
                    continue
                entity = dialog.entity
                status = getattr(entity, "status", None)
                if isinstance(status, (UserStatusEmpty, UserStatusLastMonth, UserStatusLastWeek)):
                    continue
                try:
                    msgs = await client_tg.get_messages(entity, limit=1)
                    if not msgs:
                        continue
                    last = msgs[0]
                    hours_since = (datetime.now() - last.date.replace(tzinfo=None)).total_seconds() / 3600
                    if hours_since < 48 or last.out:
                        continue
                    if not _can_re_engage(entity.id):
                        continue
                    facts = await load_memory(entity.id)
                    name = getattr(entity, 'first_name', '') or ''
                    # Собираем историю переписки
                    history_msgs = []
                    for m in reversed(list(msgs[:30])):
                        role = "assistant" if m.out else "user"
                        if m.text:
                            history_msgs.append({"role": role, "content": m.text})
                    last_her_msg = next((m.text for m in msgs if not m.out and m.text), "")
                    context_note = f"\n\nПОСЛЕДНЕЕ ЧТО ОНА ПИСАЛА: \"{last_her_msg}\"\nОтсылайся к этой теме — не пиши шаблон. Иногда используй интригу или обещание: намекни что есть что рассказать при встрече, или вспомни деталь разговора неожиданно." if last_her_msg else ""
                    if facts:
                        context_note += f"\nФакты о ней: {facts}"
                    style = random.choice(_RE_ENGAGE_STYLES)
                    resp = await groq_async(
                        model=GROQ_PRIMARY_MODEL,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT + context_note},
                            *history_msgs,
                            {"role": "user", "content": f"{style} Последнее общение {int(hours_since)} часов назад."}
                        ],
                        max_tokens=40, temperature=1.1
                    )
                    msg_text = _sanitize_msg(resp.choices[0].message.content.strip())
                    if msg_text.endswith(".") and not msg_text.endswith("..."):
                        msg_text = msg_text[:-1]
                    ok, reason = _is_sendable(msg_text)
                    if not ok or not _is_russian(msg_text):
                        print(f"🚫 Re-engage Алибек AI заблокирован ({reason}): {msg_text[:50]} → резервная фраза")
                        msg_text = random.choice(_FALLBACK_ENGAGE)
                    print(f"Re-engage → {name}: {msg_text}")
                    await asyncio.sleep(random.uniform(10, 40))
                    try:
                        await client_tg.send_message(entity, msg_text)
                        _mark_re_engaged(entity.id)
                    except FloodWaitError as fw:
                        print(f"⏳ Re-engage Алибек FloodWait {fw.seconds}с")
                        await asyncio.sleep(fw.seconds + 5)
                except _RateLimitError:
                    pass
                except Exception as e:
                    print(f"Re-engage skip: {e}")
        except Exception as e:
            print(f"Re-engage error: {e}")
        await asyncio.sleep(7200)

async def reload_improvements_loop():
    """Каждый час перезагружает уроки из improvements.txt без рестарта."""
    global SYSTEM_PROMPT
    while True:
        await asyncio.sleep(3600)
        new_prompt = _build_prompt_with_lessons()
        if new_prompt != SYSTEM_PROMPT:
            SYSTEM_PROMPT = new_prompt
            print("🔄 Уроки обновлены из improvements.txt")

async def main():
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = _build_prompt_with_lessons()
    if SYSTEM_PROMPT != BASE_PROMPT:
        print("📚 Уроки из improvements.txt загружены")
    await start_web()
    asyncio.create_task(self_ping())
    asyncio.create_task(reload_improvements_loop())
    await client_tg.start()
    print("Алибек запущен ✅")
    print(f"🦙 Локальная LLM: {_llm_status()}")
    asyncio.create_task(_llm_warmup("alibek"))  # прогрев — модель в памяти до первого сообщения
    asyncio.create_task(startup_scan())
    asyncio.create_task(catchup_scan())   # каждые 5 мин ловит пропущенные
    asyncio.create_task(re_engage())
    asyncio.create_task(ghost_check())
    await client_tg.run_until_disconnected()

while True:
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Crash: {e}, restarting in 10s...")
        import time; time.sleep(10)
