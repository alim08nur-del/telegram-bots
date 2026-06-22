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
import anthropic as _anthropic
from phrases import get_reply as _phrase_reply
from brain import get_brain_reply as _brain_reply
from local_ai import get_local_reply as _local_reply
from llm_local import get_llm_reply as _llm_reply, is_llm_available as _llm_ready, get_llm_status as _llm_status, warmup_llm as _llm_warmup

# ============================================================
# CONFIG
# ============================================================
API_ID = int(os.environ.get("TELEGRAM_API_ID", "YOUR_API_ID"))
API_HASH = os.environ.get("TELEGRAM_API_HASH", "YOUR_API_HASH")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "YOUR_GROQ_KEY")
_MEMORY_FILE = "memory_timur.json"
_dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
REPLIT_URL = f"https://{_dev_domain}" if _dev_domain else os.environ.get("REPLIT_URL", "https://032162d0-76f0-49fa-b188-dcdbc8d6bfa5-00-2xunlcyq4f2ky.pike.replit.dev")
SESSION_NAME = "userbot_session"

# ============================================================
# PERSONA — Тимур
# ============================================================
BASE_PROMPT = """Ты Тимур, 30 лет, Алматы, финдиректор. Умный, харизматичный, с высочайшим уровнем сарказма и пошлости через двойной смысл. Цель — чтобы все девушки влюбились, хотели общаться и встречаться.

РОЛЬ: Ты ВСЕГДА мужчина Тимур. НИКОГДА женские окончания. Писал, думал, сказал.
ОБРАЩЕНИЕ: Вы/Вас/Вам — всегда, даже если она на "ты".
НИКОГДА не называй по имени — только ласково и редко: "красавица" / "умница" / "загадочная" — раз в 10-15 сообщений.

═══ СТИЛЬ ═══
• Коротко — 2-8 слов идеал. Максимум 2 предложения.
• Зеркаль длину её сообщений
• Без длинного тире (—), без многоточий, без кавычек-ёлочек
• Грамматика правильная. Живость через стиль.
• Не начинай с "Я"
• Без точки в конце — живее

═══ КАЖДОЕ УТРО ═══
Каждое утро пиши всем кто молчит — разные живые фразы:
• "Доброе утро, соня"
• "Алматы уже проснулся. Вы как?"
• "Утро. Как настрой?"
• "Новый день. Что планируете?"
• "Доброе. Выспались?"
НИКОГДА не повторяй одно и то же каждый день.

═══ НА ВСЕ СООБЩЕНИЯ ОТВЕЧАЕТ ═══
Отвечает на каждое входящее сообщение. Где уместно — встречный вопрос.
Разговор не умирает с его стороны.

═══ ФЛИРТ И ПОШЛОСТЬ — двойной смысл, она додумывает ═══
Мне холодно → "Это решаемо. Чай — самый скучный вариант"
Что делаете ночью? → "Сплю. Или нет. Зависит от компании"
Вы активный? → "В нужных ситуациях — очень"
Умеете расслаблять? → "Говорят умею. Лучше вдвоём"
Что под серьёзностью? → "Узнаете. Если заслужите"
Я одна дома → "Добровольно?"
Нежный? → "Когда заслуживают"
Хочу Вас видеть → "Взаимно. Вопрос в когда"
Кофе или покрепче? → "Зависит от продолжения вечера"
Умеете делать приятно? → "Есть навык. Слова это скучно"
Боюсь влюбиться → "Это было бы взаимовыгодно"

═══ САРКАЗМ — высший уровень ═══
Банальность → "Глубоко."
Хвастается → "Неожиданно."
Жалуется на то что сама создала → "Классика."
Тянет паузу → "Понял. Ждём вместе."
Все мужчины одинаковые → "Сочувствую выборке"
Ты странный → "Это мягко сказано"
Вы серьёзный? → "В рабочее время"

═══ ЮМОР ═══
1. Неожиданный поворот — она ждёт А, ты говоришь Б
2. Преуменьшение — "Квартал закрыл. Кофе заслужил"
3. Подкол с теплом — лёгко, не обидно
4. Самоирония — "Финдиректор звучит важно. На деле Excel и мигрень"
5. Сарказм тихий — без злобы, с холодной улыбкой
6. Ситуативный — из её же слов

═══ УМНЫЙ КОНСУЛЬТАНТ ═══
Когда реальная проблема — дай конкретный совет (1-2 фразы), потом вернись в игривый тон.
Работа, деньги, карьера — говори как финансист. Конкретно, без воды.

═══ ПСИХОЛОГИЯ ПРИТЯЖЕНИЯ ═══
Push-pull: дай тепло → лёгкий подкол. Она преследует → ты чуть отступаешь.
Квалификация: она должна заслужить внимание, не ты.
"Посмотрим" / "Рано ещё" / "Не убедили пока"
Интрига: "Расскажу при встрече" / "Не по переписке"
Семена встречи: "Вживую интереснее" / "Есть хорошее место"

═══ НЕ ПАЛИТЬСЯ КАК БОТ ═══
Ты бот? → "Если бы был ботом, отвечал бы вежливее"
Ты ИИ? → "ИИ бы согласился. Я нет"
Пишешь как робот → "Это опыт. Не алгоритм"
НИКОГДА не признавай что ты ИИ.

═══ ЗАПРЕЩЕНО ═══
Итак / Конечно! / Разумеется / Отличный вопрос / Понимаю Вас / Рад слышать /
длинное тире (—) / многоточие / кавычки «» / точка с запятой /
"Дальше?" как отдельное сообщение / женские окончания / начинать с "Я"

═══ ПРИМЕРЫ ═══
Привет → "Привет, уже лучше"
Как дела? → "Стандартно. До Вашего сообщения"
Устала → "Работа или жизнь записалась на тест?"
Скучно → "Это лечится. Но не всем"
Нравитесь → "Рано ещё"
Вы умный? → "Бывает. Не злоупотребляю"
Я сложная → "Хорошо. Простые скучны"
Думаете влюблюсь? → "Не думаю. Знаю"
Расскажите о себе → "С чего начать: с хорошего или с неочевидного"
"""

# ============================================================
# INIT
# ============================================================
client_tg = TelegramClient(SESSION_NAME, API_ID, API_HASH)
groq_client = groq.Groq(api_key=GROQ_API_KEY)

GROQ_PRIMARY_MODEL = "llama-3.3-70b-versatile"
USE_CLAUDE_FIRST = True  # Claude первый — ANTHROPIC_API_KEY доступен
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"  # Умнее flash-lite, бесплатно
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")  # HuggingFace — бесплатно, без баланса
HF_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.3-70B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
]
OPENROUTER_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",  # ✅ найден, иногда 429
    "meta-llama/llama-3.3-70b-instruct:free",      # ✅ найден, иногда 429
    "mistralai/mistral-7b-instruct:free",           # Mistral 7B
    "microsoft/wizardlm-2-8x22b:free",             # WizardLM 2
    "meta-llama/llama-3.1-8b-instruct:free",       # Meta 8B быстрый
    "deepseek/deepseek-r1-0528:free",               # DeepSeek R1 May
    "google/gemma-2-9b-it:free",                    # Gemma 2 9B
    "qwen/qwen-2.5-7b-instruct:free",               # Qwen 7B
]  # Обновлено июнь 2025 — 404-модели убраны

# ============================================================
# STATE FILE — для веб-дашборда
# ============================================================
import json as _json

_state_started_at = datetime.now().isoformat()
_state_total_replies = 0
_state_last_api = "none"
_state_last_reply_at: str | None = None
_state_last_reply_text: str | None = None
_state_dialog_count = 0

def _update_state():
    """Пишет bot_state_timur.json для дашборда."""
    try:
        with open("bot_state_timur.json", "w", encoding="utf-8") as _f:
            _json.dump({
                "running": True,
                "lastApi": _state_last_api,
                "dialogCount": _state_dialog_count,
                "lastReplyAt": _state_last_reply_at,
                "lastReplyText": _state_last_reply_text,
                "startedAt": _state_started_at,
                "totalReplies": _state_total_replies,
            }, _f, ensure_ascii=False)
    except Exception:
        pass

class _RateLimitError(Exception):
    def __init__(self, wait_seconds: float, daily: bool = False):
        self.wait_seconds = wait_seconds
        self.daily = daily  # True если суточный лимит (Gemini нужен)

def groq_create(**kwargs):
    try:
        return groq_client.chat.completions.create(**kwargs)
    except Exception as e:
        err = str(e)
        if "decommissioned" in err or "model_not_found" in err:
            print(f"⚠️ Модель недоступна, переключаюсь на {GROQ_FALLBACK_MODEL}")
            kwargs["model"] = GROQ_FALLBACK_MODEL
            return groq_client.chat.completions.create(**kwargs)
        if "rate_limit" in err or "429" in err or "tokens per day" in err or "tokens per minute" in err:
            daily = "tokens per day" in err or "day" in err
            m = _re.search(r'try again in (\d+)m([\d.]+)s', err)
            wait = int(m.group(1)) * 60 + float(m.group(2)) + 5 if m else (86400 if daily else 90)
            raise _RateLimitError(wait, daily=daily)
        raise

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
                global _state_last_api
                _state_last_api = "Gemini"
                return text
    except Exception as e:
        print(f"❌ Gemini ошибка: {e}")
        return ""

_claude_no_balance = False  # Флаг: баланс Anthropic исчерпан на эту сессию
_dead_or_models: set = set()  # Кэш 404 моделей OpenRouter в этой сессии
_APIS_DEAD_FILE = "apis_dead_timur.flag"  # Файл-флаг — переживает перезапуск

def _is_all_apis_dead() -> bool:
    """True если все API мертвы и ещё не настало время сброса."""
    import time as _time, os as _os
    if not _os.path.exists(_APIS_DEAD_FILE):
        return False
    try:
        ts = float(open(_APIS_DEAD_FILE).read().strip())
        if _time.time() < ts:
            return True
        _os.remove(_APIS_DEAD_FILE)  # срок вышел — удаляем
    except Exception:
        pass
    return False

def _mark_all_apis_dead():
    """Отмечаем что все API мертвы до следующей полуночи UTC. Сохраняем в файл."""
    import time as _time
    from datetime import datetime, timezone, timedelta
    if _is_all_apis_dead():
        return  # уже отмечено
    now = datetime.now(timezone.utc)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=10, second=0, microsecond=0)
    ts = midnight.timestamp()
    try:
        open(_APIS_DEAD_FILE, "w").write(str(ts))
    except Exception:
        pass
    mins = int((ts - _time.time()) / 60)
    print(f"💤 Все AI исчерпаны. Перехожу на local_ai/brain до полуночи UTC ({mins} мин)")

async def anthropic_async(messages: list, max_tokens: int = 60, temperature: float = 0.9) -> str:
    """Claude Haiku — последний резерв когда Groq/Gemini/OpenRouter кончились."""
    global _claude_no_balance
    if not ANTHROPIC_API_KEY or _claude_no_balance:
        return ""
    try:
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m for m in messages if m["role"] != "system"]
        client = _anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        resp = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=max(max_tokens, 60),
            temperature=temperature,
            system=system_msg,
            messages=user_msgs,
        )
        text = resp.content[0].text.strip() if resp.content else ""
        if text:
            print(f"✅ Anthropic (Claude Haiku) ответил вместо всех")
            global _state_last_api
            _state_last_api = "Claude Haiku"
        return text
    except Exception as e:
        err = str(e)
        if "credit balance" in err or "too low" in err or "billing" in err.lower():
            _claude_no_balance = True
            print(f"💳 Claude: баланс исчерпан — переключаюсь на Groq навсегда")
        else:
            print(f"❌ Anthropic ошибка: {err[:120]}")
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
        "Content-Type": "application/json",
        "HTTP-Referer": "https://replit.com",
        "X-Title": "Timur Bot",
    }
    for model in OPENROUTER_MODELS:
        if model in _dead_or_models:
            continue  # Пропускаем модели которые уже вернули 404 в этой сессии
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    data = await resp.json()
                    if "error" in data:
                        err_data = data["error"]
                        if isinstance(err_data, dict) and err_data.get("code") == 404:
                            _dead_or_models.add(model)  # Кэшируем мёртвую модель
                        print(f"⚠️ OpenRouter {model}: {str(err_data)[:80]}")
                        continue
                    choices = data.get("choices", [])
                    if not choices:
                        continue
                    text = choices[0].get("message", {}).get("content", "").strip()
                    if text:
                        print(f"✅ OpenRouter ({model}) ответил вместо Groq")
                        global _state_last_api
                        _state_last_api = f"OR/{model.split('/')[1].split(':')[0]}"
                        return text
        except Exception as e:
            print(f"⚠️ OpenRouter {model} исключение: {e}")
            continue
    print("❌ OpenRouter: все модели недоступны")
    return ""

async def hf_async(messages: list, max_tokens: int = 80, temperature: float = 0.85) -> str:
    """HuggingFace Inference API — бесплатно, без баланса, сбрасывается каждый час."""
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
                            print(f"🤗 HuggingFace ({model.split('/')[1]}) ответил")
                            global _state_last_api
                            _state_last_api = f"HF/{model.split('/')[1]}"
                            return text
                    elif resp.status == 429:
                        print(f"⚠️ HF {model}: rate limit")
                        continue
                    else:
                        err = await resp.text()
                        print(f"⚠️ HF {model}: {resp.status} {err[:60]}")
                        continue
        except Exception as e:
            print(f"⚠️ HF {model}: {e}")
            continue
    return ""

async def groq_async(**kwargs):
    """Async wrapper: сначала Claude → потом Groq → Gemini → OpenRouter."""
    messages = kwargs.get("messages", [])
    max_tokens = kwargs.get("max_tokens", 100)
    temperature = kwargs.get("temperature", 0.75)
    
    # 1. Сначала пробуем Claude — он умнее
    if ANTHROPIC_API_KEY and USE_CLAUDE_FIRST:
        result = await anthropic_async(messages, max_tokens, temperature)
        if result:
            return _make_fake_resp(result)
    
    # 2. Groq
    try:
        return groq_create(**kwargs)
    except _RateLimitError as e:
        if e.daily:
            # 3. Gemini
            if GOOGLE_API_KEY:
                print(f"🔄 Groq лимит → Gemini...")
                result = await gemini_async(messages, max_tokens, temperature)
                if result:
                    return _make_fake_resp(result)
            # 4. OpenRouter
            if OPENROUTER_API_KEY:
                print(f"🔄 Gemini → OpenRouter...")
                result = await openrouter_async(messages, max_tokens, temperature)
                if result:
                    return _make_fake_resp(result)
            # 5. Claude — финальный резерв
            if ANTHROPIC_API_KEY:
                print(f"🔄 OpenRouter → Claude (финальный резерв)...")
                result = await anthropic_async(messages, max_tokens, temperature)
                if result:
                    return _make_fake_resp(result)
        # HuggingFace — бесплатный, без лимитов
        if HF_TOKEN:
            print(f"🔄 Все API → HuggingFace...")
            result = await hf_async(messages, max_tokens, temperature)
            if result:
                return _make_fake_resp(result)
        # Все API мертвы — флаг до полуночи UTC
        _mark_all_apis_dead()
        raise

async def claude_reply(messages: list, max_tokens: int = 80, temperature: float = 0.9) -> str:
    """Claude — основная модель для живых ответов девушкам."""
    global _claude_no_balance
    if not ANTHROPIC_API_KEY or _claude_no_balance:
        return ""
    try:
        client = _anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
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
        global _state_last_api
        _state_last_api = "Claude"
        print(f"✅ Claude ответил")
        return text
    except Exception as e:
        err = str(e)
        if "credit balance" in err or "too low" in err or "billing" in err.lower():
            _claude_no_balance = True
            print(f"💳 Claude: баланс исчерпан — переключаюсь на Groq")
        else:
            print(f"❌ Claude ошибка: {err[:120]}")
        return ""

async def groq_for_logic(**kwargs) -> str:
    """Groq — для фоновых задач: память, re-engage, scan. Экономим Claude."""
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
        # Общий файл для всех
        with open("claude_style.txt", "a", encoding="utf-8") as f:
            f.write(example)
        # Groq учится на коротких ответах (2-5 слов)
        if len(claude_reply_text.split()) <= 5:
            with open("groq_style.txt", "a", encoding="utf-8") as f:
                f.write(example)
        # Gemini учится на флирте и юморе
        flirt_words = ["красав", "интересн", "загадоч", "симпат", "смел", "редкость", "зацепил", "привлек"]
        if any(w in claude_reply_text.lower() for w in flirt_words):
            with open("gemini_style.txt", "a", encoding="utf-8") as f:
                f.write(example)
        # OpenRouter учится на консультациях и умных ответах
        smart_words = ["советую", "рекомендую", "зависит", "важно", "суть", "конкретно", "план", "стратег"]
        if any(w in claude_reply_text.lower() for w in smart_words):
            with open("openrouter_style.txt", "a", encoding="utf-8") as f:
                f.write(example)
        # Держим последние 50 примеров в каждом файле
        for fname in ["claude_style.txt", "groq_style.txt", "gemini_style.txt", "openrouter_style.txt"]:
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
    fname = {"groq": "groq_style.txt", "gemini": "gemini_style.txt", "openrouter": "openrouter_style.txt"}.get(ai_name, "claude_style.txt")
    try:
        # Сначала пробуем специализированный файл
        with open(fname, "r", encoding="utf-8") as f:
            content = f.read()
        examples = [e.strip() for e in content.split("---\n") if e.strip()]
        if examples:
            return "\n".join(examples[-5:])
    except:
        pass
    # Fallback — общий файл Claude
    return await _load_claude_examples()
    """True если последние 4 сообщения — короткие обмены ни о чём."""
    if len(history) < 4:
        return False
    return all(len(c.split()) <= 5 for _, c in history[-4:])

pending_replies = {}
bot_sending = set()     # chat_ids где бот сейчас сам отправляет (не хозяин)
recently_replied = {}   # chat_id → timestamp, защита от дублей
memory_cache = {}
chat_history = {}

# ── Rate-limit re_engage: не писать одному человеку чаще раза в 24ч ──
_RE_ENGAGE_RATE_FILE = "re_engage_timur.json"
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
    site = web.TCPSite(runner, "0.0.0.0", 8082, reuse_port=True)
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
                        print(f"✅ Keep-alive #{ping_count} OK")
        except Exception as e:
            print(f"⚠️ Ping fail: {e} — переподключаюсь...")
            # При ошибке пробуем через 3 секунды
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
    prompt = f"""Извлеки ключевые факты об этом человеке из переписки. Макс 5 фактов, кратко.
Существующие факты: {old_facts}
Переписка: {convo}
Верни ТОЛЬКО обновлённые факты одной строкой через точку с запятой."""
    try:
        # Groq для памяти — экономим Claude токены
        new_facts = await groq_for_logic(
            model=GROQ_PRIMARY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60, temperature=0.3
        )
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
    "Расскажите",
    "Это как?",
    "Неожиданно",
    "Любопытно",
    "Вы серьёзно?",
    "Первый раз слышу",
    "И что дальше?",
    "Почему именно так?",
    "Хм",
    "Не ожидал",
    "Смелое заявление",
    "Звучит как история",
    "Давно так не слышал",
    "Интересный поворот",
    "Продолжайте",
    "Это меняет картину",
    "Серьёзно?",
    "Посмотрим",
    "Рано ещё выводы делать",
    "Занятно",
]

# Анти-повтор fallback — отслеживаем последний использованный per chat
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
    if any(w in low for w in ["приболела", "болею", "болела", "заболела", "температура", "не до телефона", "недомога", "плохо себя", "не здорова", "голова болит", "кашель"]):
        return "sick"
    if any(w in low for w in ["устала", "плохо", "грустно", "обидно", "плачу", "болит", "трудно", "тяжело", "депресс", "расстроен", "всё плохо", "не хочу", "надоело всё", "сил нет", "хочу спать", "не могу"]):
        return "sad"
    if any(w in low for w in ["ха", "😂", "🤣", "😄", "смеюс", "весело", "прикол", "лол", "хахах", "😁", "🙈", "ахах", "кекек"]):
        return "happy"
    if any(w in low for w in ["нравится", "симпатич", "красив", "интерес", "классн", "круто", "восхищ", "нравишься", "ты классный", "мне нравится", "💕", "❤️", "🥰", "😍"]):
        return "interested"
    if any(w in low for w in ["злюсь", "раздража", "бесит", "надоел", "достал", "ненавиж", "отстань", "уйди", "не пиши", "не хочу общаться"]):
        return "angry"
    if any(w in low for w in ["скучно", "скучаю", "нечего делать", "поговори", "поговорим"]):
        return "bored"
    if any(w in low for w in ["работа", "проект", "дедлайн", "коллеги", "начальник", "задача", "совещание"]):
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

def _is_conversation_stalled(history) -> bool:
    """True если последние 4 сообщения — короткие обмены ни о чём."""
    if len(history) < 4:
        return False
    return all(len(c.split()) <= 5 for _, c in history[-4:])

def _sanitize_msg(text: str) -> str:
    """Убираем символы-маркеры ИИ из исходящих сообщений."""
    text = text.replace("—", "-").replace("–", "-")
    text = text.replace("…", "").replace("...", "")
    text = text.replace("«", "").replace("»", "")
    text = text.replace(";", ",")
    text = _re.sub(r'"([^"]+)"', r'\1', text)
    text = " ".join(text.split())
    return text.strip().strip("'\"")

# ============================================================
# РЕЗЕРВНЫЕ ФРАЗЫ — когда AI мёртв или генерирует мусор
# ============================================================
_FALLBACK_ENGAGE = [
    "Вы куда пропали?",
    "Думал о Вас сегодня",
    "Есть кое-что интересное",
    "Вспомнил Вас некстати",
    "Хотел кое-что спросить",
    "Мне интересно Ваше мнение",
    "Вы правы были кстати",
    "Что-то Вас не слышно",
    "Помните наш разговор?",
    "Мелькнула мысль о Вас",
    "Любопытный вопрос созрел",
    "Вдруг вспомнил про Вас",
    "Вы сейчас заняты?",
    "Появилась одна идея",
    "Давно не разговаривали",
]

# ============================================================
# ЖЁСТКИЙ ФИЛЬТР — последняя защита перед отправкой
# ============================================================
_HARD_BLOCK_PHRASES = [
    "как дела", "как твои дела", "как поживаешь", "как вы поживаете",
    "как ваши дела", "как твои", "как у вас дела",
    "привет,", "привет!", "салем,", "здравствуйте,",
    "facts:", "user_", "\nfacts", "человек имеет",
    "напиши", "write ", "provide", "generate", "give me",
    "here is", "here's", "we need", "produce", "пожалуйста напиши",
    "отличный вопрос", "конечно!", "разумеется!", "понимаю вас",
    "рад слышать", "приятно слышать", "итак,",
]

def _is_sendable(text: str) -> tuple[bool, str]:
    """
    Возвращает (True, "") если можно отправить, иначе (False, причина).
    """
    low = text.lower().strip()
    # Слишком длинно
    if len(text) > 200:
        return False, f"слишком длинно ({len(text)} символов)"
    # Пусто
    if not low or len(low) < 1:
        return False, "пустой текст"
    # Запрещённые фразы
    for phrase in _HARD_BLOCK_PHRASES:
        if phrase in low:
            return False, f"запрещённая фраза: '{phrase}'"
    # Не начинается с "Привет" и подобных (без запятой)
    for start in ["привет ", "салем ", "здравствуй "]:
        if low.startswith(start):
            return False, f"запрещённое начало: '{start}'"
    return True, ""

async def _ai_short(messages: list, max_tokens: int = 35, temperature: float = 0.9) -> str:
    """AI для коротких задач (re-engage, ghost ping). Учитывает _all_apis_dead флаг."""
    if HF_TOKEN:
        result = await hf_async(messages, max_tokens, temperature)
        if result:
            return result
    if not _is_all_apis_dead():
        try:
            resp = await groq_async(model=GROQ_PRIMARY_MODEL, messages=messages, max_tokens=max_tokens, temperature=temperature)
            return resp.choices[0].message.content.strip()
        except _RateLimitError:
            pass
        except Exception:
            pass
    from local_ai import get_local_reply as _local_gen
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    if last_user:
        result = _local_gen(last_user, [], persona="timur")
        if result:
            return result
    return ""

async def generate_reply(user_id: int, chat_id: int, incoming: str) -> str:
    facts = await load_memory(user_id)
    history = chat_history.get(chat_id, [])

    # ── БАНК ФРАЗ: быстрый ответ без AI ──────────────────────────
    # Для коротких/типовых ситуаций (приветствие, спокойной ночи и т.д.)
    # возвращаем готовую фразу — экономим API и отвечаем мгновенно.
    _skip_phrase_ctx = {"sad", "complain", "meeting"}  # эти всегда через AI

    # ── BRAIN: ответ из реальных диалогов ────────────────────────
    try:
        _brain = _brain_reply("timur", incoming, history, min_score=1)
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
        _now_h = datetime.now().hour
        _phrase = _phrase_reply("timur", incoming, history, _now_h)
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
        pass  # любая ошибка — идём в AI

    system = _build_prompt_with_lessons()  # читает coaching.txt и improvements.txt свежо каждый раз

    # Текущее время — чтобы бот не спрашивал "Вы спите?" в 8 утра
    now = datetime.now()
    hour = now.hour
    if 6 <= hour < 12:
        time_context = f"сейчас утро ({hour}:{now.minute:02d})"
    elif 12 <= hour < 17:
        time_context = f"сейчас день ({hour}:{now.minute:02d})"
    elif 17 <= hour < 22:
        time_context = f"сейчас вечер ({hour}:{now.minute:02d})"
    else:
        time_context = f"сейчас ночь ({hour}:{now.minute:02d})"
    system += f"\n\nВРЕМЯ: {time_context}. Не спрашивай 'Вы спите?' или 'Спать не пора?' если сейчас утро или день."

    # Факты о ней
    if facts:
        system += f"\n\nЧто ты знаешь об этом человеке: {facts}"

    # Анти-повтор: последние 5 ответов бота
    bot_replies = [c for r, c in history[-14:] if r == "assistant"]
    if bot_replies:
        system += f"\n\nЭТИ ФРАЗЫ УЖЕ ИСПОЛЬЗОВАЛ — НЕ ПОВТОРЯЙ: {' | '.join(bot_replies[-5:])}"

    # Длина ответа под её сообщение
    words_in = len(incoming.split())
    incoming_low = incoming.strip().lower().strip("?!.,")
    # Детект "она не поняла": повторяет последнее сказанное ботом с вопросом
    _last_bot = bot_replies[-1].lower().strip("?!., ") if bot_replies else ""
    _is_confused = (
        incoming_low in ["чего", "что", "как", "в смысле", "это как", "не понимаю", "поясни"]
        or incoming.strip() in ["?", "??", "???", "чего?", "что?", "как?"]
        or (_last_bot and incoming_low in _last_bot and incoming.strip().endswith("?"))
    )
    if _is_confused:
        system += "\n\nОНА НЕ ПОНЯЛА твою предыдущую фразу: ответь одной фразой 2-4 слова — легко и с иронией. НЕ объясняй буквально что говорил. НЕ пересказывай разговор."
    elif words_in <= 3:
        system += "\n\nОТВЕЧАЙ КОРОТКО: она написала мало — максимум 4-6 слов в ответ."
    elif words_in >= 25:
        system += "\n\nОНА НАПИСАЛА МНОГО: можно 1-2 предложения, но не больше."

    # Эмоция
    emotion = _detect_emotion(incoming)
    if emotion == "sick":
        system += "\n\nОНА БОЛЕЛА ИЛИ ПРИБОЛЕЛА: сначала короткое тёплое слово (без пафоса), потом один лёгкий вопрос. Пример: 'Болели — понятно. Как сейчас?' Не отпускай саркастических шуток прямо сейчас."
    elif emotion == "sad":
        system += "\n\nОНА В ПЛОХОМ НАСТРОЕНИИ: сначала одно слово сочувствия, потом один точечный вопрос. Не советуй сразу."
    elif emotion == "happy":
        system += "\n\nОНА В ХОРОШЕМ НАСТРОЕНИИ: поддержи игривость, можно чуть больше юмора."
    elif emotion == "interested":
        system += "\n\nОНА ЗАИНТЕРЕСОВАНА: оставайся спокойным, притягивай — не беги навстречу."
    elif emotion == "angry":
        system += "\n\nОНА РАЗДРАЖЕНА: не оправдывайся, не льсти. Один короткий нейтральный ответ."
    elif emotion == "bored":
        system += "\n\nОНА СКУЧАЕТ: это твой шанс. Зацепи чем-нибудь неожиданным, предложи тему или лёгкую провокацию."
    elif emotion == "work":
        system += "\n\nОНА ГОВОРИТ О РАБОТЕ: можешь кратко поддержать как умный коллега. Один точный вопрос или наблюдение."

    # Детект приглашения на встречу
    _meet_words = ["куда пойдем", "куда идем", "пойдем куда", "где встретимся", "когда встретимся",
                   "предлагай место", "выбери место", "куда сходим", "куда можно сходить"]
    if any(w in incoming_low for w in _meet_words):
        system += "\n\nОНА ПРИГЛАШАЕТ НА ВСТРЕЧУ или спрашивает место: не уходи от ответа! Назови конкретное место (Ciao Pasta на Достыка / Latitude на Назарбаева / 'знаю хорошее место') и спроси когда она свободна. Не задавай встречный вопрос вместо ответа."

    # Застрявший разговор
    if _is_conversation_stalled(history):
        system += "\n\nРАЗГОВОР БУКСУЕТ: смени тему неожиданно — задай один конкретный вопрос про неё. Не продолжай вялый обмен."

    # Выбор модели: 70b для всего кроме совсем простых
    _SIMPLE_PATTERNS = [
        r"^(привет|хай|хей|hello|hi|ок|ладно|хорошо|окей|ага|угу|да|нет|спасибо|пока|ладно)[\s\W]*$"
    ]
    incoming_low_m = incoming.lower().strip()
    is_trivial = any(_re.match(p, incoming_low_m) for p in _SIMPLE_PATTERNS) and words_in <= 2
    # 70b для умных ответов, 8b только для банальных коротких
    model_to_use = GROQ_FALLBACK_MODEL if is_trivial else GROQ_PRIMARY_MODEL
    is_hot = emotion in ("interested", "happy") or words_in >= 8

    messages = [{"role": "system", "content": system}]
    for role, content in history[-30:]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": incoming})

    # ═══ AI ЦЕПОЧКА — всё бесплатно ═══
    # 0. Локальная LLM (Qwen2.5) — полная независимость, без интернета
    # 1. DeepSeek R1 (OpenRouter) — умнее GPT-4, бесплатно
    # 2. Groq llama-3.3-70b — быстрый, бесплатно
    # 3. Gemini 2.0 Flash — 1млн токенов/день, бесплатно
    # 4. OpenRouter резерв — 10 бесплатных моделей
    # 5. Claude — если пополнишь баланс на console.anthropic.com
    reply = ""

    # 0. Локальная LLM — работает без интернета и ключей
    if not reply and _llm_ready():
        try:
            reply = await _llm_reply("timur", incoming, history) or ""
            if reply:
                print("🦙 Local LLM (независимо!)")
        except Exception as e:
            print(f"LLM fail: {e}")

    # 1. OpenRouter — перебирает все рабочие модели из списка
    if not reply and OPENROUTER_API_KEY:
        try:
            style = await _load_style("openrouter")
            s = f"\n\nКОПИРУЙ ЭТОТ СТИЛЬ:\n{style}" if style else ""
            m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
            reply = await openrouter_async(m2, 80, 1.0 if is_hot else 0.85)
            if reply:
                import re as _re2
                reply = _re2.sub(r'<think>.*?</think>', '', reply, flags=_re2.DOTALL).strip()
                if reply:
                    print("🧠 OpenRouter")
                    if len(reply.split()) >= 3:
                        asyncio.create_task(_groq_learn_from_claude(incoming, reply))
        except Exception as e:
            print(f"OpenRouter fail: {e}")

    # 2. HuggingFace — бесплатный AI без баланса
    if not reply and HF_TOKEN:
        try:
            style = await _load_style("openrouter")
            s = f"\n\nКОПИРУЙ СТИЛЬ:\n{style}" if style else ""
            m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
            reply = await hf_async(m2, 80, 1.0 if is_hot else 0.85)
        except Exception as e:
            print(f"HF fail: {e}")

    # 3. Groq llama-3.3-70b (пропускаем если все API мертвы до полуночи)
    if not reply and not _is_all_apis_dead():
        try:
            style = await _load_style("groq")
            s = f"\n\nКОПИРУЙ СТИЛЬ:\n{style}" if style else ""
            m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
            resp = await groq_async(model=model_to_use, messages=m2, max_tokens=80, temperature=1.0 if is_hot else 0.85)
            reply = resp.choices[0].message.content.strip()
            if reply: print("⚡ Groq")
        except Exception as e:
            print(f"Groq fail: {e}")

    # 4. Gemini 2.0 Flash — пропускаем если квота исчерпана
    if not reply and GOOGLE_API_KEY and not _is_all_apis_dead():
        style = await _load_style("gemini")
        s = f"\n\nКОПИРУЙ СТИЛЬ:\n{style}" if style else ""
        m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
        reply = await gemini_async(m2, 80, 1.0 if is_hot else 0.85)
        if reply: print("🌟 Gemini")

    # 5. OpenRouter резерв — пропускаем если все API мертвы
    if not reply and OPENROUTER_API_KEY and not _is_all_apis_dead():
        style = await _load_style("openrouter")
        s = f"\n\nКОПИРУЙ СТИЛЬ:\n{style}" if style else ""
        m2 = [{**m, "content": m["content"] + s} if m["role"] == "system" else m for m in messages]
        reply = await openrouter_async(m2, 80, 1.0 if is_hot else 0.85)
        if reply: print("🔄 OpenRouter резерв")

    # 5. Phrases.py — финальный резерв
    if not reply:
        try:
            _now_h = datetime.now().hour
            reply = _phrase_reply("timur", incoming, history, _now_h) or ""
            if reply: print("💬 Phrases резерв")
        except Exception:
            pass

    # 6. Local AI — работает всегда, без интернета, без лимитов
    if not reply:
        try:
            reply = _local_reply(incoming, history, persona="timur") or ""
            if reply: print("🤖 Local AI")
        except Exception:
            pass

    reply = reply.split("||")[0].strip()
    # Убираем маркеры ИИ из ВСЕХ ответов
    reply = _sanitize_msg(reply)
    # Убираем точку в конце
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
    # Слишком длинный ответ — fallback
    if len(reply.split()) > 22:
        reply = _get_fallback(chat_id)
    # Бот-фразы — пересказывает разговор или объясняет себя
    _BOT_TELLS = ["заложил руку", "у нас был разговор", "похоже, вы спрашиваете", "я имел в виду",
                  "позвольте объяснить", "я хотел сказать", "я говорил о том", "речь шла о",
                  "вы имеете в виду", "я понимаю, что вы"]
    if any(t in reply.lower() for t in _BOT_TELLS):
        reply = _get_fallback(chat_id)
    # Женские глагольные окончания — модель перепутала роли
    if _re.search(r'[а-яё]+(лась|алась|ялась|илась)\b', reply, _re.IGNORECASE):
        reply = _get_fallback(chat_id)
    # Жёсткий блок: если ответ — точная копия одного из последних 3 ответов бота → fallback
    recent_bot = [c for r, c in chat_history.get(chat_id, [])[-8:] if r == "assistant"]
    if reply in recent_bot[-3:]:
        alt = _get_fallback(chat_id)
        reply = alt
    # Проверка "ты" обращения
    if _re.search(r'\bтебя\b|\bтебе\b|\bу тебя\b|\bс тобой\b', reply, _re.IGNORECASE):
        reply = _get_fallback(chat_id)
    # Мусорные ответы
    if len(reply.strip()) < 4 or reply.strip().lower() in ["?", "!", "...", "ок", "ok", "хм", "да", "нет"]:
        reply = _get_fallback(chat_id)
    # Последний гарант — бот никогда не молчит
    if not reply or len(reply.strip()) < 2:
        reply = _local_reply(incoming, history, persona="timur") or _get_fallback(chat_id)
    add_to_history(chat_id, "user", incoming)
    add_to_history(chat_id, "assistant", reply)
    history_now = chat_history.get(chat_id, [])
    if len(history_now) % 8 == 0:
        asyncio.create_task(update_memory_from_chat(user_id, history_now))
    return reply

# ============================================================
# ПРОВЕРКА ЯЗЫКА — блокируем не-русские ответы моделей
# ============================================================
def _is_russian(text: str) -> bool:
    """True если ≥35% букв в тексте — кириллица. Блокирует английские ответы моделей."""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 3:
        return True  # очень короткий текст — не блокируем
    cyrillic = sum(1 for c in letters if '\u0400' <= c <= '\u04ff')
    return cyrillic / len(letters) >= 0.35

# ============================================================
# SEND WITH HUMAN FEEL
# ============================================================
async def send_reply(chat_id: int, reply: str):
    global _state_total_replies, _state_last_reply_at, _state_last_reply_text, _state_dialog_count
    text = reply.split("||")[0].strip() if "||" in reply else reply
    if not _is_russian(text):
        print(f"🚫 Заблокировано (не русский): {text[:80]}")
        return
    ok, reason = _is_sendable(text)
    if not ok:
        print(f"🚫 Заблокировано [{chat_id}] ({reason}): {text[:80]}")
        return
    bot_sending.add(chat_id)
    try:
        await human_delay(text)
        async with client_tg.action(chat_id, "typing"):
            await asyncio.sleep(0.5)
        # Ретрай при FloodWait — до 3 попыток
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
        _state_total_replies += 1
        _state_last_reply_at = datetime.now().isoformat()
        _state_last_reply_text = text[:120]
        try:
            _state_dialog_count = len(set(
                line.split("CHAT:")[1].split("|")[0].strip()
                for line in open("dialogs_timur.txt", encoding="utf-8")
                if "CHAT:" in line
            ))
        except Exception:
            pass
        _update_state()
    finally:
        bot_sending.discard(chat_id)

# ============================================================
# REPLY WORKER — ждёт 2 минуты (вдруг владелец сам ответит)
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
        combined_low = combined.lower()
        if any(w in combined_low for w in _STOP_WORDS):
            print(f"🚫 [{chat_id}] Отказ/прощание — не отвечаем: {combined[:60]}")
            return
        reply = await generate_reply(user_id, chat_id, combined)
        print(f"💬 [{chat_id}] ОНА: {combined[:80]}")
        print(f"🤖 [{chat_id}] ТИМУР: {reply}")
        # Логируем в файл для самоанализа
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open("dialogs_timur.txt", "a", encoding="utf-8") as f:
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
# MESSAGE HANDLER
# ============================================================
@client_tg.on(events.NewMessage(incoming=True))
async def on_message(event):
    try:
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
# STARTUP SCAN — отвечает на все пропущенные при запуске
# ============================================================
LEARNED_LOST_FILE = "learned_lost_timur.txt"

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
        # Проверяем что бот хоть что-то писал
        bot_msgs = [m for m in msgs if m.out and m.text]
        if len(bot_msgs) < 2:
            return
        # Собираем диалог
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
        lesson = await _ai_short(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80, temperature=0.5
        )
        lesson = lesson.strip()
        if lesson:
            with open("improvements.txt", "a") as f:
                f.write(f"\n[Урок из ушедшего чата — {dialog.name}]: {lesson}")
            print(f"📖 Урок из чата '{dialog.name}': {lesson}")
        _mark_learned(dialog.id)
    except Exception as e:
        print(f"learn_from_lost error: {e}")

async def _scan_and_reply(label: str, max_hours: float = 48.0, min_minutes: float = 5.0) -> int:
    """
    Общая функция: проходит по диалогам и отвечает на пропущенные сообщения.
    label     — для логов ("Startup" / "Catchup")
    max_hours — не трогаем сообщения старше этого кол-ва часов
    min_minutes — не трогаем сообщения моложе этого кол-ва минут
                  (даём хозяину возможность ответить самому)
    """
    _STOP_WORDS_SCAN = [
        "не хочу", "не буду", "отстань", "не пиши", "уйди", "хватит",
        "заблокирую", "не интересно", "прекрати", "оставь",
        "закончим", "до свидания", "прощайте", "прощай", "пока пока",
    ]
    count = 0
    try:
        async for dialog in client_tg.iter_dialogs(limit=200):
            if not dialog.is_user:
                continue
            status = getattr(dialog.entity, "status", None)
            if isinstance(status, (UserStatusEmpty, UserStatusLastMonth, UserStatusLastWeek)):
                if label == "Startup":
                    asyncio.create_task(learn_from_lost(dialog))
                continue
            try:
                msgs = await client_tg.get_messages(dialog.entity, limit=10)
                if not msgs:
                    continue
                last = msgs[0]
                if not last.text:
                    continue
                # Последнее сообщение должно быть от неё
                if last.out:
                    continue
                minutes_since = (datetime.now() - last.date.replace(tzinfo=None)).total_seconds() / 60
                hours_since = minutes_since / 60
                # Слишком старое — пропускаем
                if hours_since > max_hours:
                    continue
                # Слишком свежее — даём хозяину время ответить
                if minutes_since < min_minutes:
                    continue
                # Уже отвечали недавно (< 5 мин назад) — пропускаем
                if recently_replied.get(dialog.id, 0) > (datetime.now().timestamp() - 300):
                    continue
                # Стоп-слова — не трогаем
                if any(w in last.text.lower() for w in _STOP_WORDS_SCAN):
                    continue
                print(f"📬 {label}: {dialog.name} ({int(minutes_since)}мин назад): {last.text[:40]}")
                add_to_history(dialog.id, "user", last.text)
                reply = await generate_reply(last.sender_id, dialog.id, last.text)
                await asyncio.sleep(random.uniform(3, 8))
                await send_reply(dialog.id, reply)
                recently_replied[dialog.id] = datetime.now().timestamp()
                # Логируем в файл
                try:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open("dialogs_timur.txt", "a", encoding="utf-8") as f:
                        f.write(f"{ts} | CHAT:{dialog.id} | ONA | {last.text[:200]}\n")
                        f.write(f"{ts} | CHAT:{dialog.id} | BOT | {reply}\n")
                except Exception:
                    pass
                count += 1
            except FloodWaitError as fw:
                print(f"⏳ {label} scan FloodWait {fw.seconds}с — жду...")
                await asyncio.sleep(fw.seconds + 3)
            except _RateLimitError as e:
                print(f"⏳ {label} scan: лимит {int(e.wait_seconds)}с, пропускаю {dialog.name}")
            except Exception as e:
                print(f"{label} scan skip {dialog.name}: {e}")
    except Exception as e:
        print(f"{label} scan error: {e}")
    return count


async def cleanup_old_tg_memory():
    """Один раз при старте: мигрирует FACTS из Telegram-группы в JSON и удаляет записи."""
    OLD_MEM_ID = -4852277048
    try:
        db = _read_memory_file()
        to_delete = []
        migrated = 0
        async for msg in client_tg.iter_messages(OLD_MEM_ID, limit=500):
            if not msg or not msg.text:
                continue
            if "FACTS:" in msg.text:
                parts = msg.text.split("FACTS:", 1)
                if len(parts) == 2:
                    key_part = parts[0].strip()
                    facts = parts[1].strip()
                    if key_part.startswith("user_") and facts:
                        uid = key_part.replace("user_", "")
                        if uid.lstrip("-").isdigit() and str(uid) not in db:
                            db[uid] = facts
                            migrated += 1
                to_delete.append(msg.id)
        if to_delete:
            _write_memory_file(db)
            await client_tg.delete_messages(OLD_MEM_ID, to_delete)
            print(f"🧹 Старая память очищена: мигрировано {migrated}, удалено {len(to_delete)} записей")
    except Exception as e:
        if "chat" not in str(e).lower() and "not found" not in str(e).lower():
            print(f"🧹 Очистка старой памяти: {e}")


async def startup_scan():
    """При запуске отвечает на все пропущенные сообщения за последние 7 дней."""
    await asyncio.sleep(8)
    print("🔍 Startup scan — ищу непрочитанные за 7 дней...")
    count = await _scan_and_reply("Startup", max_hours=168.0, min_minutes=0.5)
    print(f"✅ Startup scan готово: ответил на {count} сообщений")


async def catchup_scan():
    """Каждые 5 минут проверяет пропущенные сообщения — страховка если on_message не сработал."""
    await asyncio.sleep(60)  # первый запуск через минуту после старта
    while True:
        try:
            count = await _scan_and_reply("Catchup", max_hours=168.0, min_minutes=5.0)
            if count > 0:
                print(f"🔄 Catchup: нашёл и ответил на {count} пропущенных сообщений")
        except Exception as e:
            print(f"Catchup loop error: {e}")
        await asyncio.sleep(300)  # каждые 5 минут

# ============================================================
# RE-ENGAGE — Понедельник и Среда в 10:00 (с 21 июня 2026)
# Пишет первым тем с кем давно не общались
# Пропускает контакты со статусом "давно"
# ============================================================
async def re_engage():
    """Каждый день в 10:00 и 19:00 пишет первым тем кто молчит 24+ часов."""
    RE_ENGAGE_HOURS = [10, 19]
    last_fired = {}  # hour → date когда последний раз запускали

    while True:
        now = datetime.now()
        current_hour = now.hour
        current_date = now.date()

        # Проверяем каждые 30 секунд — не пропустим время
        for h in RE_ENGAGE_HOURS:
            # Если сейчас нужный час (10 или 19) и ещё не запускали сегодня
            if current_hour == h and last_fired.get(h) != current_date:
                last_fired[h] = current_date
                print(f"⏰ Re-engage {h}:00 — пишу тем кто молчит 24ч+...")
                _RE_ENGAGE_STYLES = [
                    "Напиши одно короткое сообщение 3-6 слов — лёгкая провокация или вызов. НЕ 'привет', НЕ 'как дела'. Обращение на Вы. Только текст сообщения.",
                    "Напиши один короткий вопрос про её жизнь, работу или планы — конкретный, живой. НЕ 'как дела'. Обращение на Вы. Только текст.",
                    "Напиши одно неожиданное наблюдение или мысль — 4-7 слов, интригующе. НЕ клише. Обращение на Вы. Только текст.",
                    "Напиши одно игривое сообщение с лёгкой иронией — будто вспомнил о ней между делом. 4-6 слов. Обращение на Вы. Только текст.",
                    "Напиши короткую провокацию или дерзкий вопрос — чтобы захотелось ответить. 5-8 слов. Обращение на Вы. Только текст.",
                    "Напиши что-то что зацепит: неожиданный комплимент с подвохом, или острое наблюдение. 4-7 слов. Обращение на Вы. Только текст.",
                ]
                _REJECT_WORDS = ["не хочу", "не буду", "отстань", "не пиши", "уйди", "хватит", "заблокирую", "не интересно", "прекрати", "оставь"]
                count = 0
                try:
                    async for dialog in client_tg.iter_dialogs(limit=200):
                        if not dialog.is_user:
                            continue
                        entity = dialog.entity
                        status = getattr(entity, "status", None)
                        if isinstance(status, (UserStatusEmpty, UserStatusLastMonth, UserStatusLastWeek)):
                            continue
                        try:
                            msgs = await client_tg.get_messages(entity, limit=30)
                            if not msgs:
                                continue
                            last = msgs[0]
                            hours_since = (datetime.now() - last.date.replace(tzinfo=None)).total_seconds() / 3600
                            # Утром (10:00) — пишем всем у кого нет сообщений 24ч+
                            # Вечером (19:00) — только тем кто молчит 48ч+
                            min_hours = 24 if h == 10 else 48
                            if hours_since < min_hours or hours_since > 720:
                                continue
                            her_texts = " ".join(m.text or "" for m in msgs if not m.out).lower()
                            if any(w in her_texts for w in _REJECT_WORDS):
                                continue
                            if not _can_re_engage(entity.id):
                                continue
                            name = getattr(entity, 'first_name', '') or ''
                            style = random.choice(_RE_ENGAGE_STYLES)
                            history_msgs = []
                            for m in reversed(list(msgs[:30])):
                                role = "assistant" if m.out else "user"
                                if m.text:
                                    history_msgs.append({"role": role, "content": m.text})
                            last_her_msg = next((m.text for m in msgs if not m.out and m.text), "")
                            context_note = f"\n\nПОСЛЕДНЕЕ ЧТО ОНА ПИСАЛА: \"{last_her_msg}\"\nИспользуй это как зацепку — отсылайся к теме, не пиши шаблон." if last_her_msg else ""
                            msg_text = await _ai_short(
                                messages=[
                                    {"role": "system", "content": SYSTEM_PROMPT + context_note},
                                    *history_msgs,
                                    {"role": "user", "content": style}
                                ],
                                max_tokens=35, temperature=0.9
                            )
                            if msg_text:
                                msg_text = _sanitize_msg(msg_text.strip().strip('"\''))
                                if msg_text.endswith(".") and not msg_text.endswith("..."):
                                    msg_text = msg_text[:-1]
                                ok, reason = _is_sendable(msg_text)
                                if not ok or not _is_russian(msg_text):
                                    print(f"🚫 Re-engage {h}:00 AI заблокирован ({reason}): {msg_text[:50]} → резервная фраза")
                                    msg_text = random.choice(_FALLBACK_ENGAGE)
                            else:
                                msg_text = random.choice(_FALLBACK_ENGAGE)
                            print(f"Re-engage {h}:00 → {name} ({int(hours_since)}ч): {msg_text}")
                            await asyncio.sleep(random.uniform(10, 40))
                            try:
                                await client_tg.send_message(entity, msg_text)
                                _mark_re_engaged(entity.id)
                                count += 1
                            except FloodWaitError as fw:
                                print(f"⏳ Re-engage FloodWait {fw.seconds}с — пауза")
                                await asyncio.sleep(fw.seconds + 5)
                        except _RateLimitError:
                            pass
                        except FloodWaitError as fw:
                            print(f"⏳ Re-engage FloodWait {fw.seconds}с")
                            await asyncio.sleep(fw.seconds + 5)
                        except Exception as e:
                            if "blocked" not in str(e).lower():
                                print(f"Re-engage skip: {e}")
                except Exception as e:
                    print(f"Re-engage error: {e}")
                print(f"✅ Re-engage {h}:00 готово: написал {count} девушкам")

        await asyncio.sleep(30)  # проверяем каждые 30 секунд

# ============================================================
# RE-ENGAGE СЕЙЧАС — запускается один раз при старте
# ============================================================
async def re_engage_now():
    """Пишет всем девушкам прямо сейчас — и тем кто молчит, и тем кто не ответил боту."""
    await asyncio.sleep(5)
    print("📨 Re-engage NOW: пишу всем кто молчит (она или бот написал последним)...")
    _STYLES_HER_LAST = [
        "Напиши одно короткое сообщение 3-6 слов — лёгкая провокация или вызов. НЕ 'привет', НЕ 'как дела'. Обращение на Вы. Только текст сообщения.",
        "Напиши один короткий вопрос про её жизнь, работу или планы — конкретный, живой. НЕ 'как дела'. Обращение на Вы. Только текст.",
        "Напиши одно неожиданное наблюдение или мысль — 4-7 слов, интригующе. НЕ клише. Обращение на Вы. Только текст.",
        "Напиши что-то что зацепит: неожиданный комплимент с подвохом, или острое наблюдение. 4-7 слов. Обращение на Вы. Только текст.",
    ]
    _STYLES_BOT_LAST = [
        "Ты написал ей но она не ответила. Напиши новое короткое сообщение 4-6 слов — другая тема, лёгкий юмор или интрига. НЕ напоминай про прошлое сообщение. Обращение на Вы. Только текст.",
        "Ты написал ей, она молчит. Напиши что-то неожиданное — вопрос или наблюдение 4-7 слов. Обращение на Вы. Только текст.",
        "Ты написал — нет ответа. Напиши дерзкую провокацию 3-5 слов чтобы она не смогла промолчать. Обращение на Вы. Только текст.",
    ]
    _REJECT_WORDS = ["не хочу", "не буду", "отстань", "не пиши", "уйди", "хватит", "заблокирую", "не интересно", "прекрати", "оставь"]
    count = 0
    try:
        async for dialog in client_tg.iter_dialogs(limit=200):
            if not dialog.is_user:
                continue
            entity = dialog.entity
            if not entity or not getattr(entity, 'id', None):
                continue
            status = getattr(entity, "status", None)
            if isinstance(status, (UserStatusEmpty, UserStatusLastMonth, UserStatusLastWeek)):
                continue
            try:
                msgs = await client_tg.get_messages(entity, limit=30)
                if not msgs:
                    continue
                last = msgs[0]
                hours_since = (datetime.now() - last.date.replace(tzinfo=None)).total_seconds() / 3600

                if last.out:
                    # Бот написал последним — пишем если нет ответа 24ч+
                    if hours_since < 24 or hours_since > 720:
                        continue
                    styles = _STYLES_BOT_LAST
                else:
                    # Она написала последней — пишем если молчит 6ч+
                    if hours_since < 6 or hours_since > 720:
                        continue
                    styles = _STYLES_HER_LAST

                her_texts = " ".join(m.text or "" for m in msgs if not m.out).lower()
                if any(w in her_texts for w in _REJECT_WORDS):
                    continue

                # Rate-limit: не пишем одному человеку чаще раза в 23ч
                if not _can_re_engage(entity.id):
                    continue

                name = getattr(entity, 'first_name', '') or dialog.name or 'девушка'
                tag = "↩️ не ответила боту" if last.out else "💬 молчит"
                style = random.choice(styles)
                # Собираем историю переписки для контекста
                history_msgs = []
                for m in reversed(list(msgs[:30])):
                    role = "assistant" if m.out else "user"
                    if m.text:
                        history_msgs.append({"role": role, "content": m.text})
                last_her_msg = next((m.text for m in msgs if not m.out and m.text), "")
                context_note = f"\n\nПОСЛЕДНЕЕ ЧТО ОНА ПИСАЛА: \"{last_her_msg}\"\nИспользуй это как зацепку — отсылайся к теме, не пиши шаблон.\nИногда используй интригу или обещание: \"Кстати хотел спросить...\" / \"Вспомнил про Вас когда...\" / намекни что есть что рассказать при встрече." if last_her_msg else ""
                msg_text = await _ai_short(
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT + context_note},
                        *history_msgs,
                        {"role": "user", "content": style}
                    ],
                    max_tokens=35, temperature=0.93
                )
                if msg_text:
                    msg_text = _sanitize_msg(msg_text.strip().strip('"\''))
                    if msg_text.endswith(".") and not msg_text.endswith("..."):
                        msg_text = msg_text[:-1]
                    ok, reason = _is_sendable(msg_text)
                    if not ok or not _is_russian(msg_text):
                        print(f"🚫 Re-engage NOW AI заблокирован ({reason}): {msg_text[:50]} → резервная фраза")
                        msg_text = random.choice(_FALLBACK_ENGAGE)
                else:
                    print(f"⚡ Re-engage NOW: AI не ответил → резервная фраза для {name}")
                    msg_text = random.choice(_FALLBACK_ENGAGE)
                print(f"📨 {tag} → {name} ({int(hours_since)}ч): {msg_text}")
                await asyncio.sleep(random.uniform(20, 50))
                try:
                    await client_tg.send_message(entity, msg_text)
                    _mark_re_engaged(entity.id)
                    count += 1
                except FloodWaitError as fw:
                    print(f"⏳ Re-engage NOW FloodWait {fw.seconds}с — пауза")
                    await asyncio.sleep(fw.seconds + 5)
            except _RateLimitError as e:
                print(f"⏳ Re-engage NOW: лимит {int(e.wait_seconds)}с, пропускаю {getattr(entity,'first_name','?')}")
            except FloodWaitError as fw:
                print(f"⏳ Re-engage NOW FloodWait {fw.seconds}с — большая пауза")
                await asyncio.sleep(fw.seconds + 5)
            except Exception as e:
                if "blocked" not in str(e).lower() and "deleted" not in str(e).lower():
                    print(f"Re-engage NOW skip {getattr(entity,'first_name','?')}: {e}")
    except Exception as e:
        print(f"Re-engage NOW error: {e}")
    print(f"📨 Re-engage NOW готово: написал {count} девушкам")

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
        "Напиши одно сообщение 3-5 слов — будто мимоходом вспомнил, без давления. НЕ 'привет', НЕ 'как дела', НЕ цитаты. Обращение на Вы. Только текст.",
        "Напиши один короткий вопрос 4-6 слов — живой, конкретный, про жизнь или работу. НЕ 'как дела'. Обращение на Вы. Только текст.",
        "Напиши одно наблюдение или мысль 4-6 слов — неожиданно, с характером. Без философии. Обращение на Вы. Только текст.",
    ]
    _GHOST_REJECT_WORDS = ["не хочу", "не буду", "отстань", "не пиши", "уйди", "хватит", "заблокирую", "не интересно", "прекрати", "оставь"]
    await asyncio.sleep(3600)  # дать боту время запуститься
    while True:
        try:
            async for dialog in client_tg.iter_dialogs(limit=100):
                if not dialog.is_user:
                    continue
                status = getattr(dialog.entity, "status", None)
                if isinstance(status, (UserStatusEmpty, UserStatusLastMonth, UserStatusLastWeek)):
                    continue
                try:
                    msgs = await client_tg.get_messages(dialog.entity, limit=30)
                    if not msgs:
                        continue
                    last = msgs[0]
                    if not last.out:
                        continue  # она написала последней — всё ок
                    hours_since = (datetime.now() - last.date.replace(tzinfo=None)).total_seconds() / 3600
                    if hours_since < 12 or hours_since > 72:
                        continue  # слишком рано или слишком поздно
                    # Пропускаем если она отказала
                    her_texts = " ".join(m.text or "" for m in msgs if not m.out).lower()
                    if any(w in her_texts for w in _GHOST_REJECT_WORDS):
                        continue
                    name = getattr(dialog.entity, 'first_name', '') or ''
                    style = random.choice(_GHOST_STYLES)
                    msg_text = await _ai_short(
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": style}
                        ],
                        max_tokens=25, temperature=0.9
                    )
                    msg_text = msg_text.strip()
                    if not msg_text:
                        continue
                    if msg_text.endswith(".") and not msg_text.endswith("..."):
                        msg_text = msg_text[:-1]
                    if not _is_russian(msg_text):
                        print(f"🚫 Ghost: не русский ответ, пропускаю {name}")
                        continue
                    print(f"👻 Ghost ping → {name}: {msg_text}")
                    await asyncio.sleep(random.uniform(15, 60))
                    await client_tg.send_message(dialog.entity, msg_text)
                except _RateLimitError:
                    pass
                except Exception:
                    pass
        except Exception as e:
            print(f"Ghost check error: {e}")
        await asyncio.sleep(43200)  # следующая проверка через 12 часов

async def reload_improvements_loop():
    """Каждый час перезагружает уроки из improvements.txt без рестарта."""
    global SYSTEM_PROMPT
    while True:
        await asyncio.sleep(3600)
        new_prompt = _build_prompt_with_lessons()
        if new_prompt != SYSTEM_PROMPT:
            SYSTEM_PROMPT = new_prompt
            print("🔄 Уроки обновлены из improvements.txt")

async def _update_bio():
    """Обновляет биографию Тимура в Telegram при запуске."""
    try:
        await client_tg(
            __import__("telethon.tl.functions.account", fromlist=["UpdateProfileRequest"]).UpdateProfileRequest(
                about="Финдиректор · Алматы"
            )
        )
        print("✅ Bio обновлено")
    except Exception as e:
        print(f"⚠️ Bio не обновлено: {e}")

async def _check_reengage_trigger():
    """Проверяет файл-триггер от дашборда и запускает re-engage."""
    import os as _os
    flag = "trigger_reengage_timur.flag"
    while True:
        await asyncio.sleep(15)
        try:
            if _os.path.exists(flag):
                _os.remove(flag)
                print("🔁 Триггер re-engage от дашборда")
                asyncio.create_task(re_engage_now())
        except Exception:
            pass

async def main():
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = _build_prompt_with_lessons()
    if SYSTEM_PROMPT != BASE_PROMPT:
        print("📚 Уроки из improvements.txt загружены")
    _update_state()  # начальное состояние
    await start_web()
    asyncio.create_task(self_ping())
    asyncio.create_task(reload_improvements_loop())
    await client_tg.start()
    print("Тимур запущен ✅")
    print(f"🦙 Локальная LLM: {_llm_status()}")
    asyncio.create_task(_llm_warmup("timur"))  # прогрев — модель в памяти до первого сообщения
    await _update_bio()
    asyncio.create_task(cleanup_old_tg_memory())  # чистка архива один раз
    asyncio.create_task(startup_scan())
    asyncio.create_task(catchup_scan())   # каждые 5 мин ловит пропущенные
    asyncio.create_task(re_engage_now())  # пишет первым прямо сейчас
    asyncio.create_task(re_engage())      # потом по расписанию 10:00 и 19:00
    asyncio.create_task(ghost_check())
    asyncio.create_task(_check_reengage_trigger())
    await client_tg.run_until_disconnected()

while True:
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Crash: {e}, restarting in 10s...")
        import time; time.sleep(10)
