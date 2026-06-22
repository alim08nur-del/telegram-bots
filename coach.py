import os
import time
import groq
from datetime import datetime

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
LOG_FILES = {
    "Тимур": "dialogs_timur.txt",
    "Алибек": "dialogs_alibek.txt",
}
COACHING_FILE = "coaching.txt"
COACH_INTERVAL = 600  # каждые 10 минут


def read_last_lines(filepath, n=300):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return lines[-n:]


def parse_turns(lines):
    turns = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split(" | ", 3)
        if len(parts) < 4:
            continue
        ts_str, chat_part, role, text = parts
        try:
            ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            chat_id = chat_part.replace("CHAT:", "").strip()
        except Exception:
            continue
        turns.append((ts, chat_id, role.strip(), text.strip()))
    return turns


def extract_exchanges(turns, limit=20):
    """Берёт последние N полных обменов (ОНА → БОТ)."""
    chats = {}
    for ts, chat_id, role, text in turns:
        chats.setdefault(chat_id, []).append((ts, role, text))

    exchanges = []
    for chat_id, msgs in chats.items():
        for i, (ts, role, text) in enumerate(msgs):
            if role == "BOT" and i > 0:
                prev_role = msgs[i - 1][1]
                if prev_role == "ONA":
                    exchanges.append({
                        "chat_id": chat_id,
                        "ona": msgs[i - 1][2],
                        "bot": text,
                        "context": [msgs[j] for j in range(max(0, i - 3), i - 1)]
                    })
    return exchanges[-limit:]


def coach_exchanges(exchanges, persona, client):
    if not exchanges:
        return None

    formatted = []
    for ex in exchanges:
        ctx = "\n".join([f"{'ОНА' if r=='ONA' else 'БОТ'}: {t}" for _, r, t in ex["context"]])
        block = f"Контекст:\n{ctx}\nОНА: {ex['ona']}\nБОТ: {ex['bot']}"
        formatted.append(block)

    text = "\n\n---\n\n".join(formatted)

    prompt = f"""Ты строгий коуч по флирту. Бот "{persona}" — уверенный, остроумный мужчина 30 лет, Алматы. Обращение на Вы. Должен нравиться девушкам — быть умным, смешным, немного дерзким.

Проверь каждый ответ бота по критериям:
1. ОСТРОУМИЕ: есть неожиданный поворот, подкол, двойной смысл? Или скучно и предсказуемо?
2. ФЛИРТ: есть лёгкая пошлинка, намёк, игривость? Или сухо?
3. ЖИВОСТЬ: звучит как живой мужчина или как ChatGPT?
4. ОБРАЩЕНИЕ: только Вы/Вас/Вам?
5. ДЛИНА: не слишком длинно? (больше 15 слов — уже подозрительно)

Для КАЖДОГО слабого ответа напиши:
БЫЛО: [что бот написал]
НАДО: [как должен был ответить Тимур — коротко, остроумно, с флиртом]

Примеры правильного стиля Тимура:
"Скучно" → "Это лечится"
"Ты опасный" → "Для кого как"
"Я не такая" → "Жаль"
"Нравишься" → "Рано ещё"
"Целоваться умеешь?" → "Жалоб не поступало"

Если всё хорошо — напиши "Норм". Максимум 12 строк.

Диалоги:
{text}"""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Groq ошибка: {e}")
        return None


def run_coach(client):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🎯 Коуч проверяет диалоги...")

    all_feedback = []

    for bot_name, log_file in LOG_FILES.items():
        lines = read_last_lines(log_file, 300)
        if not lines:
            print(f"  {bot_name}: лог пуст")
            continue

        turns = parse_turns(lines)
        exchanges = extract_exchanges(turns, limit=20)
        print(f"  {bot_name}: проверяю {len(exchanges)} обменов...")

        if not exchanges:
            continue

        feedback = coach_exchanges(exchanges, bot_name, client)
        if feedback and feedback.strip().lower() != "норм":
            all_feedback.append(f"[Поправки от коуча — {datetime.now().strftime('%H:%M')}]\n{feedback}")
            print(f"  {bot_name}: найдены замечания")
        else:
            print(f"  {bot_name}: всё норм ✅")

    if all_feedback:
        with open(COACHING_FILE, "w", encoding="utf-8") as f:
            f.write("\n\n".join(all_feedback))
        print(f"  📋 Поправки записаны в {COACHING_FILE}")
    else:
        # Очищаем файл если всё хорошо
        with open(COACHING_FILE, "w", encoding="utf-8") as f:
            f.write("")
        print(f"  ✅ Поправок нет — боты на уровне")

    print(f"  Следующая проверка через {COACH_INTERVAL // 60} минут")


def main():
    if not GROQ_API_KEY:
        print("GROQ_API_KEY не найден")
        return

    client = groq.Groq(api_key=GROQ_API_KEY)
    print("🎯 Коуч запущен. Проверяю каждые 10 минут.")

    while True:
        try:
            run_coach(client)
        except Exception as e:
            print(f"  Ошибка коуча: {e}")
        time.sleep(COACH_INTERVAL)


if __name__ == "__main__":
    main()
