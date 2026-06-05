# Feature 1: Screenshot / image input 📸

**Status:** 💭 Idea · **Effort:** ~30–45 min · **Priority:** High (low effort, high impact)

## The problem

Today the only way to get data in is to **export a WhatsApp chat as a `.txt`** and upload it.
That export is a fiddly, multi-tap flow that most people won't bother with — it's the single
biggest point of friction in the app. Taking a **screenshot**, on the other hand, is muscle
memory for everyone.

Removing this friction could be the difference between "neat demo" and "thing people
actually use."

## Proposed solution

Let users upload **one or more screenshots** of their chat. `gpt-4o-mini` is already
**multimodal** (it reads images natively), so it can do the OCR *and* the task extraction in
a single call — no separate OCR library needed.

Because the LLM call is already isolated in `extractor.py`, this is a contained change:

1. **UI** — offer two input methods, e.g. tabs: `📄 Text file` / `📸 Screenshots`.
   The screenshot uploader uses `st.file_uploader(type=["png", "jpg", "jpeg"],
   accept_multiple_files=True)`.
2. **Encoding** — base64-encode each image and pass them as image content blocks in the
   OpenAI message, alongside the same extraction prompt we already use.
3. **Prompt tweak** — tell the model the images are **sequential / chronological** so it
   reads a multi-screenshot conversation in order.
4. **Output** — unchanged: same structured `Task` list flows into the existing visualizations.

### Sketch

```python
# extractor.py — same function, new input path
def extract_tasks_from_images(image_bytes_list, today):
    content = [{"type": "text", "text": "These are sequential chat screenshots..."}]
    for img in image_bytes_list:
        b64 = base64.b64encode(img).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })
    # ...same system prompt + JSON-mode call as the text path
```

## Design choices & considerations

- **Keep both input methods.** For very long chats, the text export still extracts more
  reliably than screenshots, so don't remove it — offer screenshots as the *easier default*.
- **Multiple screenshots.** A chat won't fit in one image; support several and signal order.
- **Cost.** Images cost more tokens than text — roughly a cent or two per run instead of
  fractions of a cent. Still trivial, but worth noting.
- **Image quality.** Cropped / low-res screenshots may hurt extraction; consider a gentle
  hint in the UI ("make sure names and messages are legible").

## Why it fits the architecture

The extraction step is already provider-isolated, and everything downstream (validation,
charts, `.ics` export, the future chatbot) operates on the `Task` list — which is identical
regardless of whether the source was text or an image. This feature is purely additive.
