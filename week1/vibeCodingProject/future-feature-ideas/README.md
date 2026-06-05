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

## Suggested build order

1. **Screenshot input** — quick win, removes the biggest friction (exporting chats is painful). ~30–45 min.
2. **Conversational AI editor** — the standout "agentic" feature; needs a small `Task.id` groundwork first. ~1–1.5 hr.

The two features are **independent and composable**: screenshots change the *input* to the
extraction step, while the chatbot operates on the *output*. Neither blocks the other.
