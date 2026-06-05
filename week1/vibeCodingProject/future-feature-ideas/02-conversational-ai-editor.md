# Feature 2: Conversational AI editor 💬

**Status:** 💭 Idea · **Effort:** ~1–1.5 hr · **Priority:** High (the standout "agentic" feature)

## The problem

On the results page, the only way to fix or change tasks is the **editable table** — which
works but is mechanical. Users think in natural language: *"move the dog pickup to Saturday
and split the cooking between us."* Letting them just *say* that is a real wow moment, and
it's exactly the kind of agentic, natural-language-driven interaction the product should have.

## Proposed solution: a tool-calling chatbot

Add a chat panel on the results page (`st.chat_input` + `st.chat_message`). Crucially, the
model does **not** rewrite the task list directly — it **calls functions** (tools) that we
execute deterministically against the tasks in `st.session_state`.

### Toolset

```
add_task(title, assignee, category, due_date, priority, effort_minutes, notes)
edit_task(task_id, <any fields to change>)
delete_task(task_id)
reassign_task(task_id, new_assignee)
set_status(task_id, status)
```

### The loop (per user message)

1. User types: *"move the dog pickup to Saturday and split the cooking between us."*
2. We send the model: the **current tasks (with IDs)** + the **available tools** + the message.
3. The model responds with one or more tool calls, e.g.
   `edit_task(id=2, due_date="2026-06-06")` and `add_task(...)`.
4. **We** apply those operations to the task list — the model never touches the data directly.
5. Rerun → calendar, sunburst, and workload charts all update instantly (this plumbing
   already exists, since the editable table mutates the same session state).
6. Echo a short confirmation: *"✅ Moved 'Pick up Bruno' to Sat; added a cooking task for Utsav."*

## Why tool-calling (vs. full-rewrite)

We considered two approaches. **Tool-calling wins** for this product:

| | Tool-calling (chosen) | Full-rewrite |
|---|---|---|
| How | Model emits targeted `add/edit/delete` ops | Model returns the whole updated list each turn |
| Safety | High — can't drop/reword unrelated tasks | Risk of accidental edits to untouched tasks |
| "Agentic" factor | High — the model *acts* through tools | Low — it just regenerates text |
| Inspectable | Yes — log exactly what the AI decided to do | Harder to see what changed |
| Build effort | Slightly more | Slightly less |

The safety + inspectability + agentic story make tool-calling clearly worth the small extra
effort — and it demos beautifully (you can literally show "here's what the AI decided to do").

## Prerequisite: stable task IDs

Tools need to reference *which* task, but `Task` currently has no ID. So before/with this
feature we'd add a stable `id` field to the `Task` model. Small change, but it ripples through
a few places:

- `models.py` — add `id` (e.g. a short uuid or incrementing int), assign on creation.
- The editable table — preserve IDs across edits.
- Chart hover data — optional, but handy for debugging.

## Considerations

- **Don't lose unrelated tasks.** Pass stable IDs and instruct "only change what's requested."
- **Show what changed.** A per-turn summary builds user trust ("Moved X, reassigned Y").
- **Conversation memory.** Keep the chat history in `st.session_state` so follow-ups like
  "actually, make that Sunday instead" work.
- **Undo.** Optional but nice — snapshot the task list before each AI edit so a mistake is
  reversible.

## Why it fits the architecture

Charts and `.ics` export already re-render from `st.session_state` tasks on every rerun, so
the chatbot only needs to mutate that state — no changes to the visualization layer. It's
also independent of the input source (text or screenshots), since it operates on the
*output* task list.
