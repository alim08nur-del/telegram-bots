import os
import time
import groq
from datetime import datetime

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
LOG_FILES = {
    "Тимур": "dialogs_timur.txt",
    "Алибек": "dialogs_alibek.txt",
}
IMPROVEMENTS_FILE = "improvements.txt"
REVIEW_INTERVAL = 3600  # каждый час
SILENCE_HOURS = 3


def read_last_lines(filepath, n=2000):
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


def find_failed_replies(turns):
    """Ответы бота после которых девушка замолчала 3+ часов."""
    now = datetime.now()
    failed = []
    chats = {}
    for ts, chat_id, role, text in turns:
        chats.setdefault(chat_id, []).append((ts, role, text))

    for chat_id, msgs in chats.items():
        for i, (ts, role, text) in enumerate(msgs):
            if role != "BOT":
                continue
            next_ona_ts = None
            for j in range(i + 1, len(msgs)):
                if msgs[j][1] == "ONA":
                    next_ona_ts = msgs[j][0]
                    break
            hours_since = (now - ts).total_seconds() / 3600
            if next_ona_ts is None and hours_since >= SILENCE_HOURS:
                context = msgs[max(0, i - 3): i + 1]
                context_str = "\n".join(
                    [f"{'ОНА' if r == 'ONA' else 'БОТ'}: {t}" for _, r, t in context]
                )
                failed.append(context_str)
    return failed


def find_successful_exchanges(turns):
    """Диалоги где девушка ответила 3+ раза подряд — значит зацепило."""
    chats = {}
    for ts, chat_id, role, text in turns:
        chats.setdefault(chat_id, []).append((ts, role, text))

    successes = []
    for chat_id, msgs in chats.items():
        # Ищем серии где она отвечает активно (3+ ONA подряд в окне 10 сообщений)
        for i in range(len(msgs) - 5):
            window = msgs[i:i + 10]
            ona_count = sum(1 for _, r, _ in window if r == "ONA")
            bot_count = sum(1 for _, r, _ in window if r == "BOT")
            if ona_count >= 3 and bot_count >= 2:
                excerpt = "\n".join(
                    [f"{'ОНА' if r == 'ONA' else 'БОТ'}: {t}" for _, r, t in window]
                )
                successes.append(excerpt)
                break  # один пример на чат достаточно
    return successes


def analyze_failures(failed_exchanges, client):
    if not failed_exchanges:
        return None
    sample = failed_exchanges[:10]
    text = "\n\n---\n\n".join(sample)
    prompt = f"""Ты эксперт по флирту в переписке. После этих ответов девушка замолчала и не написала:

{text}

Дай 3-4 конкретных урока что изменить чтобы девушки не уходили. Кратко, без воды. Только уроки."""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400, temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Groq ошибка (провалы): {e}")
        return None


def analyze_successes(success_exchanges, client):
    if not success_exchanges:
        return None
    sample = success_exchanges[:6]
    text = "\n\n---\n\n".join(sample)
    prompt = f"""Ты эксперт по флирту в переписке. В этих диалогах девушка активно отвечала и вовлекалась:

{text}

Выдели 2-3 конкретных приёма что именно сработало — что нужно делать чаще. Кратко, без воды. Только приёмы."""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300, temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Groq ошибка (успехи): {e}")
        return None


def run_review(client):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🔍 Запускаю самоанализ...")

    # Объединяем логи обоих ботов — они один человек
    all_turns = []
    total_lines = 0
    for bot_name, log_file in LOG_FILES.items():
        lines = read_last_lines(log_file, 2000)
        if not lines:
            print(f"  {bot_name}: лог пуст, пропускаю")
            continue
        turns = parse_turns(lines)
        all_turns.extend(turns)
        total_lines += len(turns)
        print(f"  {bot_name}: {len(turns)} реплик загружено")

    if not all_turns:
        print("  ✅ Логов нет — боты ещё не писали")
        print(f"  Следующая проверка через {REVIEW_INTERVAL // 3600} часа")
        return

    failed = find_failed_replies(all_turns)
    successes = find_successful_exchanges(all_turns)
    print(f"  Всего: {total_lines} реплик | {len(failed)} провалов | {len(successes)} удачных диалогов")

    lessons_parts = []

    if failed:
        fail_analysis = analyze_failures(failed, client)
        if fail_analysis:
            lessons_parts.append(f"[ЧТО НЕ РАБОТАЕТ — избегай]\n{fail_analysis}")
            print("  ✅ Анализ провалов готов")

    if successes:
        success_analysis = analyze_successes(successes, client)
        if success_analysis:
            lessons_parts.append(f"[ЧТО РАБОТАЕТ — делай чаще]\n{success_analysis}")
            print("  ✅ Анализ успехов готов")

    if lessons_parts:
        with open(IMPROVEMENTS_FILE, "w", encoding="utf-8") as f:
            f.write(f"Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("\n\n".join(lessons_parts))
        print(f"  ✅ Уроки записаны в {IMPROVEMENTS_FILE} (оба бота подхватят через час)")
    else:
        print("  ✅ Паттернов не найдено — боты справляются")

    print(f"  Следующая проверка через {REVIEW_INTERVAL // 3600} часа")


def main():
    if not GROQ_API_KEY:
        print("GROQ_API_KEY не найден, самоанализ невозможен")
        return

    client = groq.Groq(api_key=GROQ_API_KEY)
    print("🧠 Self-review запущен. Анализирую каждый час.")

    while True:
        try:
            run_review(client)
        except Exception as e:
            print(f"  Ошибка самоанализа: {e}")
        time.sleep(REVIEW_INTERVAL)


if __name__ == "__main__":
    main()
