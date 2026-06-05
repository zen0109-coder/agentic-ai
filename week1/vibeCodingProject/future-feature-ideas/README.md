# 💡 Future Feature Ideas

A running list of features we've discussed for **chat2tasks** but haven't built yet.
Each idea has its own doc with the problem, a proposed solution, design choices, and
considerations.

> Context: the core product turns a conversation into an organized, visual, accountable
> plan. It started as a household task manager but generalizes to office work, friends'
> trip planning, event prep — anything that can be broken into tasks.

## Ideas

| # | Idea | Status | One-liner |
|---|------|--------|-----------|
| 1 | [Screenshot / image input](./01-screenshot-image-input.md) | 💭 Idea | Let users upload chat **screenshots** instead of exporting a `.txt`. |
| 2 | [Conversational AI editor](./02-conversational-ai-editor.md) | 💭 Idea | Let users **talk to the AI** to change the plan in real time. |
| 3 | [Navigable multi-week calendar](./03-navigable-multi-week-calendar.md) | 💭 Idea | Page through weeks so tasks beyond the current Mon–Sun week are visible. |

## Suggested build order

1. **Screenshot input** — quick win, removes the biggest friction (exporting chats is painful). ~30–45 min.
2. **Navigable multi-week calendar** — fixes a real usability gap; `calendar_data()` already takes a `week_start` arg, so it's mostly UI + state. ~30–45 min.
3. **Conversational AI editor** — the standout "agentic" feature; needs a small `Task.id` groundwork first. ~1–1.5 hr.

These ideas are largely **independent**: screenshots change the *input* to extraction, the
calendar is a *view* change, and the chatbot operates on the *output* task list.
