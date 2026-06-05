"""Plotly figure builders + small data shapers for the dashboard.

Pure functions only — no Streamlit imports — so the chart logic stays testable
and the app layer just renders what it gets back.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from models import NO_CATEGORY, Task


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def tasks_to_frame(tasks: list[Task]) -> pd.DataFrame:
    """Flatten tasks into a DataFrame the charts can group over."""
    rows = [
        {
            "title": t.title,
            "assignee": t.assignee,
            "category": t.category or NO_CATEGORY,
            "due_date": t.due_date,
            "priority": t.priority,
            "effort_minutes": t.effort_minutes,
            "status": t.status,
            "notes": t.notes,
        }
        for t in tasks
    ]
    return pd.DataFrame(rows)


def calendar_data(tasks: list[Task], week_start: date | None = None) -> dict:
    """Group dated tasks into a rolling 7-day window for the calendar grid.

    Returns {"days": [(label, date, [tasks]), ...x7], "undated": [tasks],
             "week_start": date, "week_end": date}.
    By default the window starts on `week_start` (today if not given), so e.g.
    uploading on a Thursday shows Thursday -> next Wednesday rather than a fixed
    Monday-Sunday week. Day labels are derived from the actual dates.
    """
    dated = [t for t in tasks if t.due_date]
    if week_start is None:
        week_start = date.today()  # rolling window: today + next 6 days

    week_end = week_start + timedelta(days=6)
    days = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_tasks = sorted(
            [t for t in dated if t.due_date == day],
            key=lambda t: {"high": 0, "medium": 1, "low": 2}.get(t.priority, 1),
        )
        days.append((day.strftime("%A"), day, day_tasks))  # label e.g. "Thursday"

    # Anything without a date, or dated outside the 7-day window, goes in the
    # bucket so no task silently disappears from the view.
    other = [
        t for t in tasks
        if not t.due_date or not (week_start <= t.due_date <= week_end)
    ]
    return {"days": days, "undated": other, "week_start": week_start, "week_end": week_end}


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def category_sunburst(tasks: list[Task], colors: dict[str, str]) -> go.Figure:
    """Person -> Category -> Task rings, sized by effort, colored by person."""
    df = tasks_to_frame(tasks)
    if df.empty:
        return _empty_fig("No tasks to chart yet")

    fig = px.sunburst(
        df,
        path=["assignee", "category", "title"],
        values="effort_minutes",
        color="assignee",
        color_discrete_map=colors,
        custom_data=["priority"],
    )
    fig.update_traces(
        insidetextorientation="radial",
        hovertemplate="<b>%{label}</b><br>%{value} min<extra></extra>",
    )
    fig.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=520)
    return fig


def workload_split(
    tasks: list[Task], colors: dict[str, str], basis: str = "count"
) -> tuple[go.Figure, go.Figure]:
    """Return (donut, category_bar). basis is "count" or "effort"."""
    df = tasks_to_frame(tasks)
    if df.empty:
        empty = _empty_fig("No tasks to chart yet")
        return empty, empty

    value_col = "effort_minutes" if basis == "effort" else "_count"
    label = "minutes" if basis == "effort" else "tasks"
    if basis != "effort":
        df["_count"] = 1

    # Donut: each person's share.
    per_person = df.groupby("assignee", as_index=False)[value_col].sum()
    donut = px.pie(
        per_person,
        names="assignee",
        values=value_col,
        hole=0.55,
        color="assignee",
        color_discrete_map=colors,
    )
    donut.update_traces(
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value} " + label + " (%{percent})<extra></extra>",
    )
    total = int(per_person[value_col].sum())
    donut.update_layout(
        margin=dict(t=10, l=0, r=0, b=0),
        height=380,
        showlegend=False,
        annotations=[dict(text=f"{total}<br>{label}", x=0.5, y=0.5,
                          font_size=18, showarrow=False)],
    )

    # Grouped bar: who owns which category.
    per_cat = df.groupby(["category", "assignee"], as_index=False)[value_col].sum()
    bar = px.bar(
        per_cat,
        x="category",
        y=value_col,
        color="assignee",
        color_discrete_map=colors,
        barmode="group",
    )
    bar.update_layout(
        margin=dict(t=10, l=0, r=0, b=0),
        height=380,
        xaxis_title="",
        yaxis_title=label.capitalize(),
        legend_title="",
    )
    return donut, bar


def timeline(tasks: list[Task], colors: dict[str, str]) -> go.Figure:
    """Gantt-style timeline of dated tasks, colored by person."""
    dated = [t for t in tasks if t.due_date]
    if not dated:
        return _empty_fig("No dated tasks to place on a timeline")

    rows = [
        {
            "title": t.title,
            "assignee": t.assignee,
            "start": pd.Timestamp(t.due_date),
            # give point-in-time tasks a visible 1-day bar
            "end": pd.Timestamp(t.due_date) + pd.Timedelta(days=1),
            "priority": t.priority,
        }
        for t in dated
    ]
    df = pd.DataFrame(rows).sort_values("start")
    fig = px.timeline(
        df,
        x_start="start",
        x_end="end",
        y="title",
        color="assignee",
        color_discrete_map=colors,
        custom_data=["priority"],
    )
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>%{customdata[0]} priority<extra></extra>"
    )
    fig.update_layout(margin=dict(t=10, l=0, r=0, b=0), height=480, legend_title="")
    return fig


def urgency_buckets(tasks: list[Task], today: date | None = None) -> dict[str, int]:
    """Counts of pending tasks by urgency relative to today."""
    today = today or date.today()
    soon = today + timedelta(days=2)
    buckets = {"Overdue": 0, "Due soon": 0, "Upcoming": 0, "No date": 0}
    for t in tasks:
        if t.status == "done":
            continue
        if not t.due_date:
            buckets["No date"] += 1
        elif t.due_date < today:
            buckets["Overdue"] += 1
        elif t.due_date <= soon:
            buckets["Due soon"] += 1
        else:
            buckets["Upcoming"] += 1
    return buckets


def _empty_fig(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font_size=15)
    fig.update_layout(
        height=360,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(t=10, l=0, r=0, b=0),
    )
    return fig
