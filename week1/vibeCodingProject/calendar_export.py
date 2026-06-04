"""Export tasks to an .ics calendar file (importable into Google/Apple/Outlook).

No OAuth, no accounts — just bytes the user can download and open.
"""

from __future__ import annotations

from ics import Calendar, Event

from models import Task


def tasks_to_ics(tasks: list[Task], assignee: str | None = None) -> bytes:
    """Build an .ics file from tasks.

    Only tasks with a due_date become events (a calendar needs dates).
    If `assignee` is given, only that person's tasks are included.
    """
    cal = Calendar()
    for t in tasks:
        if t.due_date is None:
            continue
        if assignee is not None and t.assignee != assignee:
            continue

        event = Event()
        event.name = t.title
        event.begin = t.due_date.isoformat()
        event.make_all_day()

        details = [
            f"Assignee: {t.assignee}",
            f"Category: {t.category}",
            f"Priority: {t.priority}",
            f"Estimated effort: {t.effort_minutes} min",
        ]
        if t.notes:
            details.append(f"Notes: {t.notes}")
        event.description = "\n".join(details)
        event.categories = {t.category}

        cal.events.add(event)

    return cal.serialize().encode("utf-8")
