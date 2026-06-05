# Feature 3: Navigable / scrollable multi-week calendar 🗓️

**Status:** 💭 Idea · **Effort:** ~30–45 min · **Priority:** Medium (real usability gap)

## The problem

The weekly calendar only renders a **single Mon–Sun week** — specifically the week
containing the *earliest* dated task (see `calendar_data()` in `viz.py`). Any task dated
outside that one week falls into the **"No date / other weeks"** bucket instead of appearing
on the grid.

This breaks in a very common case: if you upload a chat **mid-week** (say a Thursday), tasks
naturally spill into next week and beyond — "haircut next Sunday," "rent on the 1st." Those
tasks exist and are counted in the charts, but you **can't see them on the calendar**, which
is exactly where you'd look. The calendar should let you move through time.

## Proposed solution

Make the calendar **navigable across weeks**. Two viable designs:

### Option A — Week navigation (recommended, simplest)
Keep the existing 7-column Mon–Sun grid, but add controls to change *which* week is shown:

- `◀ Previous week` · `Today` · `Next week ▶` buttons above the grid.
- Track the displayed week in `st.session_state["calendar_week_start"]`.
- The heavy lifting is already there: `calendar_data(tasks, week_start=...)` **already
  accepts a `week_start` argument** — today the app just never passes it. So this is mostly
  UI plumbing + state.
- Bonus: show a small hint like "3 tasks in later weeks →" so users know to navigate.

### Option B — Scrollable multi-week view
Render **every week from the earliest to the latest dated task**, stacked vertically as a
single scrollable page (week label + 7-day row, repeated). Shows everything at once, no
clicking — but can get long if tasks span far-apart dates (e.g. a rent task next month).

**Recommendation:** start with **Option A** (clean, bounded, familiar). Option B is a nice
follow-up, or could be offered as a "show all weeks" toggle.

## Sketch (Option A)

```python
# app.py — render_calendar
if "calendar_week_start" not in st.session_state:
    st.session_state["calendar_week_start"] = None  # default: week of earliest task

c1, c2, c3 = st.columns([1, 1, 1])
if c1.button("◀ Previous week"):
    st.session_state["calendar_week_start"] -= timedelta(days=7)
if c2.button("Today"):
    st.session_state["calendar_week_start"] = this_monday()
if c3.button("Next week ▶"):
    st.session_state["calendar_week_start"] += timedelta(days=7)

data = viz.calendar_data(tasks, week_start=st.session_state["calendar_week_start"])
# ...render the 7 columns as today
```

## Considerations

- **Default week.** Keep defaulting to the week of the earliest task (or "this week" if all
  tasks are future) so the first view is useful without clicking.
- **The "other weeks" bucket.** Once navigation exists, this bucket should hold **only
  truly undated tasks** — dated tasks are now reachable by paging. Update the label/logic in
  `calendar_data()` accordingly.
- **Empty weeks.** Paging into a week with no tasks should show a friendly "Nothing this
  week" rather than a blank grid.
- **State reset.** Reset `calendar_week_start` when the user clicks "Start over" / loads a
  new chat, so stale offsets don't carry over.

## Why it fits the architecture

`calendar_data()` is already parameterized by `week_start`, and the calendar renders purely
from that returned structure — so this is almost entirely a UI + session-state change with a
small tweak to the "other weeks" bucket logic. No impact on extraction, other charts, or
`.ics` export.
