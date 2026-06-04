# 🏠 Household Task Manager

**Turn your household WhatsApp chat into an organized, fairly-split, visual task board.**

Me and my wife juggle a lot of small tasks every week — picking up and dropping the dog
at the sitter's, paying bills, groceries, weekend plans, cooking, the random "we're out of X."
They all live as scattered reminders in our WhatsApp group chat, nobody really *owns* anything,
and that quietly builds resentment. This app fixes the **visibility and accountability** problem:
export the chat, let an LLM turn it into a clean, assigned task list, and *see* who is doing what.

---

## How it works

```
WhatsApp chat (.txt)
      │  export & upload
      ▼
  LLM extraction  (OpenAI gpt-4o-mini, structured JSON)
      │  detects participants, assigns tasks, estimates effort, resolves dates
      ▼
  Structured tasks  ──►  Interactive visualizations  ──►  .ics calendar download
                          • 📅 Weekly calendar
                          • 🌅 Category sunburst
                          • ⚖️ Workload split (count & effort)
```

1. **Import** — upload your exported chat `.txt` (or hit *Try the sample chat*).
2. **Extract** — `gpt-4o-mini` reads the messages and produces a structured task list:
   each task gets an **assignee**, **category**, **due date**, **priority** and an
   **effort estimate** (minutes).
3. **Explore** — switch between three views to understand the week, then download
   `.ics` files to drop the tasks into Google / Apple / Outlook calendars.

---

## Features

- 📤 Upload a WhatsApp chat export (or use the bundled sample — no API key needed for that).
- 🤖 AI extraction with **auto-detected participants**, assignees, categories, priorities,
  due dates, and **effort estimates**.
- 📅 **Weekly calendar** — Mon–Sun grid, each task a colored chip by person.
- 🌅 **Category sunburst** — Person → Category → Task, click to zoom.
- ⚖️ **Workload split** — donut + per-category bar, toggle between **task count** and
  **effort (minutes)** so 5 quick errands ≠ 2 hour-long jobs. This is the accountability payoff.
- ✏️ **Editable table** — fix anything the AI mis-parsed; charts update live.
- 🗓️ **.ics export** — per person or everyone, importable into any calendar app.

---

## Tech stack

| Piece | Choice |
|-------|--------|
| Language / env | Python 3.12, managed by [`uv`](https://docs.astral.sh/uv/) |
| UI | [Streamlit](https://streamlit.io/) |
| LLM | OpenAI `gpt-4o-mini` |
| Charts | [Plotly](https://plotly.com/python/) |
| Calendar files | [`ics`](https://pypi.org/project/ics/) |
| Validation | [Pydantic](https://docs.pydantic.dev/) |

---

## Setup & run

```bash
# 1. Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install dependencies
uv sync

# 3. Add your OpenAI key
cp .env.example .env
#   then edit .env and paste your key:  OPENAI_API_KEY=sk-...

# 4. Run
uv run streamlit run app.py
```

The app opens in your browser. No key yet? You can still click **Try the sample chat**
to explore the app with bundled demo data.

---

## How to export a WhatsApp chat

1. Open the group chat.
2. **iPhone:** tap the chat name → *Export Chat* → *Without Media*.
   **Android:** ⋮ menu → *More* → *Export chat* → *Without Media*.
3. Save / share the resulting `.txt` file, then upload it in the app.

---

## Cost

Running on `gpt-4o-mini`, a typical week's chat costs **~$0.004 per run** (less than half a
cent). Even heavy testing stays well under a dollar.

---

## Deploying to Streamlit Community Cloud

This app is ready to deploy for free at [share.streamlit.io](https://share.streamlit.io).

1. Push this project to a **GitHub repo** (the `.env` is git-ignored and will NOT be pushed — good).
2. On [share.streamlit.io](https://share.streamlit.io), click **New app**, pick your repo/branch,
   and set the main file to `app.py`.
3. In **Advanced settings → Secrets**, add your key in TOML form:
   ```toml
   OPENAI_API_KEY = "sk-...your-real-key..."
   ```
   The app bridges `st.secrets` into the environment automatically (see `_bootstrap_secrets`
   in `app.py`), so the same code works locally (`.env`) and in the cloud (secrets).
4. Deploy. You'll get a shareable `*.streamlit.app` URL.

Dependencies are read from `requirements.txt` (regenerate with `uv export --no-hashes
--no-emit-project -o requirements.txt` after changing deps).

> 💡 **Cost note:** when deployed with *your* key, every visitor's extraction is billed to
> you. Keep the link private, or switch to a "bring your own key" field if you make it public.

## Roadmap / stretch goals

- 🔗 Live two-way **Google Calendar** sync (OAuth) instead of `.ics` downloads.
- 💾 Persistence so tasks and "done" state survive a refresh.
- 🔁 Recurring task detection (e.g. weekly dog dropoff).
- 📈 Multi-week history and trends.

---

## About

Built for **Week 1 of an Agentic AI course** — assignment: *take an input of data and
produce a fancy visualization*. Here the "data" is messy human chat and the "visualization"
is an interactive, accountability-focused task dashboard.
