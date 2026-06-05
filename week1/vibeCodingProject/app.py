"""Household Task Manager — Streamlit app.

Two screens:
  1. Import   — upload a WhatsApp chat .txt (or use the bundled sample)
  2. Explore  — staged loading, metrics, three view tabs, editable table, .ics export
"""

from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

import viz
from calendar_export import tasks_to_ics
from extractor import extract_tasks, has_api_key
from models import Task, build_color_map, participants_from_tasks


def _bootstrap_secrets() -> None:
    """Bridge Streamlit Cloud secrets into the environment.

    Locally the key comes from .env (loaded in extractor.py). On Streamlit
    Community Cloud there's no .env — the key lives in st.secrets — so copy it
    into os.environ where the OpenAI SDK and has_api_key() expect it.
    """
    if os.getenv("OPENAI_API_KEY"):
        return
    try:
        if "OPENAI_API_KEY" in st.secrets:
            os.environ["OPENAI_API_KEY"] = str(st.secrets["OPENAI_API_KEY"])
    except Exception:
        pass  # no secrets file present (pure local dev) — that's fine


_bootstrap_secrets()

st.set_page_config(page_title="Household Task Manager", page_icon="🏠", layout="wide")

SAMPLE_PATH = Path(__file__).parent / "sample_chat.txt"
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


# --------------------------------------------------------------------------- #
# State helpers
# --------------------------------------------------------------------------- #
def init_state() -> None:
    st.session_state.setdefault("screen", "import")
    st.session_state.setdefault("chat_text", None)
    st.session_state.setdefault("tasks", None)
    st.session_state.setdefault("participants", [])
    st.session_state.setdefault("source_label", "")


def go_to(screen: str) -> None:
    st.session_state["screen"] = screen


def reset() -> None:
    for k in ("chat_text", "tasks", "participants", "source_label"):
        st.session_state[k] = None if k != "participants" else []
    st.session_state["screen"] = "import"


# --------------------------------------------------------------------------- #
# Screen 1 — Import
# --------------------------------------------------------------------------- #
def render_import() -> None:
    st.title("🏠 Household Task Manager")
    st.markdown(
        "##### Turn your household WhatsApp chat into an organized, "
        "fairly-split, visual task board."
    )
    st.write(
        "Stop losing track of who's picking up the dog, paying the bills or doing the "
        "grocery run. Drop in your chat and let AI sort it into an accountable plan."
    )

    if not has_api_key():
        st.info(
            "No `OPENAI_API_KEY` found — that's fine! You can still explore the app "
            "with the **sample chat** below. Add a key to `.env` to process your own chats.",
            icon="💡",
        )

    st.divider()
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.subheader("📤 Upload your chat")
        uploaded = st.file_uploader(
            "Export a WhatsApp chat (Without Media) and upload the .txt",
            type=["txt"],
            label_visibility="visible",
        )
        if uploaded is not None:
            st.session_state["chat_text"] = uploaded.read().decode("utf-8", errors="ignore")
            st.session_state["source_label"] = uploaded.name
            st.success(f"Loaded **{uploaded.name}** ✓")

    with col2:
        st.subheader("🧪 Or try the sample")
        st.write("A realistic week of household chatter — dog sitter, bills, groceries, plans.")
        if st.button("Try the sample chat", width="stretch"):
            st.session_state["chat_text"] = SAMPLE_PATH.read_text(encoding="utf-8")
            st.session_state["source_label"] = "sample_chat.txt"
            st.success("Sample chat loaded ✓")

    st.divider()

    ready = bool(st.session_state.get("chat_text"))
    if ready:
        st.caption(f"Source: **{st.session_state['source_label']}** — ready to extract.")
    if st.button(
        "Extract tasks ✨",
        type="primary",
        disabled=not ready,
        width="stretch",
    ):
        go_to("explore")
        st.rerun()


# --------------------------------------------------------------------------- #
# Screen 2 — Explore
# --------------------------------------------------------------------------- #
def run_extraction() -> None:
    """Run extraction with a staged, honest 'loading' display."""
    with st.status("Processing your chat…", expanded=True) as status:
        st.write("📖 Reading the chat…")
        time.sleep(0.4)
        st.write("🤖 Extracting & assigning tasks with AI…")
        try:
            tasks, participants = extract_tasks(
                st.session_state["chat_text"], today=date.today()
            )
        except RuntimeError as e:
            status.update(label="Extraction failed", state="error")
            st.error(str(e))
            st.button("← Back", on_click=reset)
            st.stop()

        if not participants:
            participants = participants_from_tasks(tasks)
        st.session_state["tasks"] = tasks
        st.session_state["participants"] = participants
        st.write(f"📊 Building views for {len(tasks)} tasks…")
        time.sleep(0.3)
        status.update(label=f"Done — found {len(tasks)} tasks", state="complete")


def tasks_to_editor_df(tasks: list[Task]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "title": t.title,
                "assignee": t.assignee,
                "category": t.category,
                "due_date": t.due_date,
                "priority": t.priority,
                "effort_minutes": t.effort_minutes,
                "status": t.status,
                "notes": t.notes,
            }
            for t in tasks
        ]
    )


def _is_blank(v) -> bool:
    """True for None / NaN / NaT — the empty cells of a newly added editor row."""
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except (TypeError, ValueError):
        return False


def editor_df_to_tasks(df: pd.DataFrame) -> list[Task]:
    tasks: list[Task] = []
    for rec in df.to_dict(orient="records"):
        # Drop blank/NaN cells so the Task model's defaults & validators apply
        # instead of choking on a float NaN (e.g. an empty new row). Without
        # this, str(NaN) == "nan" sneaks past a naive truthiness check.
        clean = {k: v for k, v in rec.items() if not _is_blank(v)}
        title = clean.get("title")
        if not title or not str(title).strip():
            continue  # skip rows with no real title (incl. wholly empty new rows)
        tasks.append(Task.model_validate(clean))
    return tasks


def render_metrics(tasks: list[Task], participants: list[str]) -> None:
    buckets = viz.urgency_buckets(tasks)
    cols = st.columns(2 + len(participants[:3]))
    cols[0].metric("Total tasks", len(tasks))
    cols[1].metric("⚠️ Overdue", buckets["Overdue"])
    for i, name in enumerate(participants[:3]):
        person_tasks = [t for t in tasks if t.assignee == name]
        hours = sum(t.effort_minutes for t in person_tasks) / 60
        cols[2 + i].metric(f"{name}", f"{len(person_tasks)} tasks", f"{hours:.1f} h")


def render_explore() -> None:
    # Lazily run extraction the first time we land here.
    if st.session_state.get("tasks") is None:
        run_extraction()

    tasks: list[Task] = st.session_state["tasks"]
    participants: list[str] = st.session_state["participants"] or participants_from_tasks(tasks)
    colors = build_color_map(participants)

    top = st.columns([0.8, 0.2])
    with top[0]:
        st.title("📋 Your week, sorted")
        st.caption(f"From **{st.session_state.get('source_label', 'your chat')}**")
    with top[1]:
        st.write("")
        st.button("← Start over", on_click=reset, width="stretch")

    if not has_api_key():
        st.warning(
            "**Demo mode:** no `OPENAI_API_KEY` was found, so these are built-in **sample "
            "tasks** — your uploaded chat was *not* processed. Add your key to `.env` and "
            "restart the app to extract tasks from your own chat.",
            icon="⚠️",
        )

    if not tasks:
        st.warning("No tasks were found in this chat. Try a different export.")
        return

    render_metrics(tasks, participants)
    st.divider()

    tab_cal, tab_sun, tab_load, tab_time = st.tabs(
        ["📅 Weekly calendar", "🌅 Category sunburst", "⚖️ Workload split", "📊 Timeline"]
    )

    with tab_cal:
        render_calendar(tasks, colors)

    with tab_sun:
        st.caption("Each ring zooms in: **Person → Category → Task**. Size = estimated effort.")
        st.plotly_chart(viz.category_sunburst(tasks, colors), width="stretch")

    with tab_load:
        basis_label = st.radio(
            "Measure fairness by:",
            ["Number of tasks", "Time / effort (minutes)"],
            horizontal=True,
        )
        basis = "effort" if basis_label.startswith("Time") else "count"
        donut, bar = viz.workload_split(tasks, colors, basis=basis)
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("**Share per person**")
            st.plotly_chart(donut, width="stretch")
        with c2:
            st.markdown("**Who owns which category**")
            st.plotly_chart(bar, width="stretch")

    with tab_time:
        st.plotly_chart(viz.timeline(tasks, colors), width="stretch")

    st.divider()
    render_editor_and_export(tasks, participants)


def render_calendar(tasks: list[Task], colors: dict[str, str]) -> None:
    data = viz.calendar_data(tasks)
    ws, we = data["week_start"], data["week_end"]
    st.caption(
        f"Next 7 days — **{ws.strftime('%a, %b %d')} → {we.strftime('%a, %b %d')}** — "
        "colored by person."
    )

    cols = st.columns(7, gap="small")
    for col, (name, day, day_tasks) in zip(cols, data["days"]):
        with col:
            st.markdown(f"**{name[:3]}**<br><span style='color:gray'>{day.strftime('%b %d')}</span>",
                        unsafe_allow_html=True)
            if not day_tasks:
                st.markdown("<span style='color:#ccc'>—</span>", unsafe_allow_html=True)
            for t in day_tasks:
                _task_chip(t, colors)

    if data["undated"]:
        st.markdown("###### 📌 No date / outside the next 7 days")
        chip_cols = st.columns(4)
        for i, t in enumerate(data["undated"]):
            with chip_cols[i % 4]:
                _task_chip(t, colors, show_date=True)


def _task_chip(t: Task, colors: dict[str, str], show_date: bool = False) -> None:
    color = colors.get(t.assignee, "#BAB0AC")
    done = "text-decoration:line-through;opacity:0.55;" if t.status == "done" else ""
    flag = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t.priority, "")
    when = f" · {t.due_date.strftime('%b %d')}" if (show_date and t.due_date) else ""
    st.markdown(
        f"""
        <div style="background:{color}1A;border-left:4px solid {color};
                    border-radius:6px;padding:6px 8px;margin-bottom:6px;{done}">
            <div style="font-size:0.8rem;font-weight:600;">{flag} {t.title}</div>
            <div style="font-size:0.7rem;color:{color};">{t.assignee} · {t.effort_minutes}m{when}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_editor_and_export(tasks: list[Task], participants: list[str]) -> None:
    st.subheader("✏️ Review & fix tasks")
    st.caption("Edit anything the AI got wrong — every chart above updates when you apply changes.")

    df = tasks_to_editor_df(tasks)
    edited = st.data_editor(
        df,
        width="stretch",
        num_rows="dynamic",
        column_config={
            "due_date": st.column_config.DateColumn("Due date"),
            "priority": st.column_config.SelectboxColumn(
                "Priority", options=["high", "medium", "low"]
            ),
            "status": st.column_config.SelectboxColumn(
                "Status", options=["pending", "done"]
            ),
            "effort_minutes": st.column_config.NumberColumn("Effort (min)", min_value=5, step=5),
        },
        key="task_editor",
    )

    if st.button("Apply edits 🔄"):
        st.session_state["tasks"] = editor_df_to_tasks(edited)
        st.session_state["participants"] = participants_from_tasks(st.session_state["tasks"])
        st.rerun()

    st.subheader("🗓️ Export to your calendar")
    st.caption("Download an .ics file and open it to add these tasks to Google / Apple / Outlook.")
    cols = st.columns(len(participants) + 1)
    cols[0].download_button(
        "📥 Everyone",
        data=tasks_to_ics(tasks),
        file_name="household_tasks.ics",
        mime="text/calendar",
        width="stretch",
    )
    for i, name in enumerate(participants):
        cols[i + 1].download_button(
            f"📥 {name}",
            data=tasks_to_ics(tasks, assignee=name),
            file_name=f"tasks_{name.lower()}.ics",
            mime="text/calendar",
            width="stretch",
        )


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
def main() -> None:
    init_state()
    if st.session_state["screen"] == "import":
        render_import()
    else:
        render_explore()


if __name__ == "__main__":
    main()
