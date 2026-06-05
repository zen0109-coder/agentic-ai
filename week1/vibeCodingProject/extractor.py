"""Turn raw WhatsApp chat text into structured, assigned tasks.

All OpenAI-specific code lives in this one module, so switching providers later
is a single-function change. If there's no API key configured, the extractor
falls back to a small bundled demo set so the UI is still fully explorable.
"""

from __future__ import annotations

import json
import os
from datetime import date

from dotenv import load_dotenv

from models import Task, tasks_from_dicts

load_dotenv()

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """\
You are a meticulous household assistant. You read an exported group chat between \
people who live together and extract the concrete, actionable to-do tasks they \
mention or agree on.

Rules:
- Detect the real participant names from the chat (the senders, e.g. "Priya", "Utsav").
- Output ONE task per distinct actionable item (e.g. "pay electricity bill",
  "drop dog at sitter", "book brunch table"). Do NOT create tasks for pure chit-chat.
- assignee: the person who agreed to / is responsible for the task. If the chat makes
  it clear someone took it on, use that name. If genuinely unclear, use "Unassigned".
- category: a short bucket like Pets, Bills, Groceries, Chores, Errands, Social,
  Health, Home, Car, Plans. Reuse categories consistently.
- due_date: resolve relative references ("Friday", "this weekend", "tomorrow", "the 5th")
  to an absolute ISO date (YYYY-MM-DD), anchored to TODAY -- NOT to the chat's message
  timestamps (the chat may be days or weeks old). If no date is implied, use null.
  Saturday/Sunday = "this weekend".
  HARD RULE: due_date must NEVER be earlier than TODAY. If a reference would land before
  TODAY, set it to TODAY. If a task is already completed (status "done"), set due_date to null.
- priority: "high", "medium", or "low" based on urgency in the conversation.
- effort_minutes: your best integer estimate of how long the task realistically takes
  (a quick errand ~15, groceries ~45, fixing a faucet ~90, etc.).
- status: "pending" unless the chat clearly says it's already done.
- notes: a short helpful detail if present (e.g. "sitter closes at 6pm"), else "".

Return ONLY a JSON object of the form:
{"participants": ["Name1", "Name2"], "tasks": [ {task}, {task}, ... ]}
where each task has keys: title, assignee, category, due_date, priority,
effort_minutes, status, notes.
"""


def has_api_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _enforce_future_dates(tasks: list[Task], today: date) -> list[Task]:
    """Safety net: no task should be scheduled in the past.

    Completed tasks lose their (past) date; any pending task dated before TODAY
    is clamped to TODAY. Mirrors the prompt's HARD RULE in case the model slips.
    """
    for t in tasks:
        if t.status == "done":
            t.due_date = None
        elif t.due_date is not None and t.due_date < today:
            t.due_date = today
    return tasks


def extract_tasks(
    chat_text: str, today: date | None = None
) -> tuple[list[Task], list[str]]:
    """Extract tasks + participant names from raw chat text.

    Returns (tasks, participants). Falls back to demo data when no API key is set.
    Raises RuntimeError with a friendly message on API failure.
    """
    today = today or date.today()

    if not has_api_key():
        tasks, participants = _demo_tasks(today)
        return _enforce_future_dates(tasks, today), participants

    # Imported lazily so the app still runs (demo mode) without the dep configured.
    from openai import OpenAI

    client = OpenAI()
    user_prompt = (
        f"TODAY is {today.isoformat()} ({today.strftime('%A')}). "
        f"All due_date values must be {today.isoformat()} or later.\n\n"
        f"Here is the exported chat:\n\n{chat_text}"
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:  # surface a clean message to the UI layer
        raise RuntimeError(f"OpenAI request failed: {e}") from e

    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Model returned invalid JSON: {e}") from e

    tasks = tasks_from_dicts(data.get("tasks", []))
    participants = [str(p).strip() for p in data.get("participants", []) if str(p).strip()]

    # Backfill participants from the tasks themselves if the model omitted them.
    for t in tasks:
        if t.assignee not in participants and t.assignee != "Unassigned":
            participants.append(t.assignee)

    return _enforce_future_dates(tasks, today), participants


def _demo_tasks(today: date) -> tuple[list[Task], list[str]]:
    """Pre-baked tasks used when no API key is present, so the UI is demoable."""
    from datetime import timedelta

    # Anchor demo dates to "this week" relative to today.
    monday = today - timedelta(days=today.weekday())

    def d(offset: int) -> str:
        return (monday + timedelta(days=offset)).isoformat()

    raw = [
        {"title": "Drop Bruno at the sitter", "assignee": "Utsav", "category": "Pets",
         "due_date": d(2), "priority": "high", "effort_minutes": 30, "status": "done",
         "notes": "Sitter opens 7:30am, leave by 7"},
        {"title": "Pick up Bruno from the sitter", "assignee": "Priya", "category": "Pets",
         "due_date": d(4), "priority": "high", "effort_minutes": 30,
         "notes": "Sitter closes at 6pm"},
        {"title": "Pay electricity bill ($140)", "assignee": "Utsav", "category": "Bills",
         "due_date": d(4), "priority": "high", "effort_minutes": 15, "status": "done"},
        {"title": "Grocery run", "assignee": "Priya", "category": "Groceries",
         "due_date": d(1), "priority": "medium", "effort_minutes": 45, "status": "done",
         "notes": "dog food, coffee, eggs, pasta, dish soap, paper towels"},
        {"title": "Buy spinach (was out of stock)", "assignee": "Priya",
         "category": "Groceries", "due_date": None, "priority": "low",
         "effort_minutes": 20},
        {"title": "Book brunch table for 4", "assignee": "Priya", "category": "Social",
         "due_date": d(5), "priority": "medium", "effort_minutes": 10,
         "notes": "Saturday 11am, place near the park"},
        {"title": "Fix leaky kitchen faucet", "assignee": "Utsav", "category": "Home",
         "due_date": d(5), "priority": "medium", "effort_minutes": 90},
        {"title": "Transfer rent", "assignee": "Utsav", "category": "Bills",
         "due_date": d(29), "priority": "high", "effort_minutes": 10,
         "notes": "due 1st of next month, transfer on the 30th"},
        {"title": "Call garage to book car service", "assignee": "Utsav",
         "category": "Car", "due_date": d(3), "priority": "medium",
         "effort_minutes": 15, "notes": "weird noise"},
        {"title": "Order birthday gift for Aditi", "assignee": "Priya",
         "category": "Social", "due_date": d(6), "priority": "medium",
         "effort_minutes": 20, "notes": "gift card + a book, birthday Sunday"},
        {"title": "Call dentist to book cleanings for both", "assignee": "Utsav",
         "category": "Health", "due_date": d(2), "priority": "medium",
         "effort_minutes": 15},
        {"title": "Water the plants", "assignee": "Utsav", "category": "Chores",
         "due_date": d(2), "priority": "low", "effort_minutes": 10},
    ]
    tasks = tasks_from_dicts(raw)
    return tasks, ["Priya", "Utsav"]
