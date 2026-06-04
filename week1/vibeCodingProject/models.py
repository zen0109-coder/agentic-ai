"""Data model for an extracted household task, plus small shared helpers.

Kept free of Streamlit / OpenAI imports so it can be reused and tested anywhere.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# A colorblind-friendly palette reused across every chart so a person keeps the
# same color in the calendar, sunburst, donut and bars.
PALETTE = [
    "#4C78A8",  # blue
    "#F58518",  # orange
    "#54A24B",  # green
    "#E45756",  # red
    "#72B7B2",  # teal
    "#B279A2",  # purple
    "#FF9DA6",  # pink
    "#9D755D",  # brown
]

PRIORITIES = ("high", "medium", "low")
STATUSES = ("pending", "done")
UNASSIGNED = "Unassigned"
NO_CATEGORY = "Other"


class Task(BaseModel):
    """One actionable household task extracted from the chat."""

    title: str
    assignee: str = UNASSIGNED
    category: str = NO_CATEGORY
    due_date: Optional[date] = None
    priority: str = "medium"
    effort_minutes: int = 30
    status: str = "pending"
    notes: str = ""

    @field_validator("due_date", mode="before")
    @classmethod
    def _parse_due_date(cls, v):
        """Accept ISO strings, date/datetime objects, or empty -> None."""
        if v in (None, "", "null", "none"):
            return None
        if isinstance(v, datetime):
            return v.date()
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            # Tolerate a full timestamp by keeping just the date part.
            return date.fromisoformat(v.strip()[:10])
        return None

    @field_validator("priority", mode="before")
    @classmethod
    def _norm_priority(cls, v):
        v = str(v or "").strip().lower()
        return v if v in PRIORITIES else "medium"

    @field_validator("status", mode="before")
    @classmethod
    def _norm_status(cls, v):
        v = str(v or "").strip().lower()
        return v if v in STATUSES else "pending"

    @field_validator("assignee", mode="before")
    @classmethod
    def _norm_assignee(cls, v):
        v = str(v or "").strip()
        return v or UNASSIGNED

    @field_validator("category", mode="before")
    @classmethod
    def _norm_category(cls, v):
        v = str(v or "").strip()
        return v or NO_CATEGORY

    @field_validator("effort_minutes", mode="before")
    @classmethod
    def _norm_effort(cls, v):
        try:
            n = int(round(float(v)))
        except (TypeError, ValueError):
            return 30
        # Clamp to something sane (5 min .. 8 hours).
        return max(5, min(n, 480))


def tasks_from_dicts(raw: list[dict]) -> list[Task]:
    """Validate a list of raw dicts (e.g. from the LLM) into Task objects.

    Skips any individual entry that fails validation rather than dropping
    the whole batch.
    """
    out: list[Task] = []
    for item in raw or []:
        try:
            out.append(Task.model_validate(item))
        except Exception:
            continue
    return out


def participants_from_tasks(tasks: list[Task]) -> list[str]:
    """Stable, de-duplicated list of assignees seen across the tasks."""
    seen: list[str] = []
    for t in tasks:
        if t.assignee not in seen:
            seen.append(t.assignee)
    return seen


def build_color_map(participants: list[str]) -> dict[str, str]:
    """Map each participant to a stable color from the palette."""
    colors: dict[str, str] = {}
    for i, name in enumerate(participants):
        colors[name] = PALETTE[i % len(PALETTE)]
    colors.setdefault(UNASSIGNED, "#BAB0AC")  # grey for unassigned
    return colors
