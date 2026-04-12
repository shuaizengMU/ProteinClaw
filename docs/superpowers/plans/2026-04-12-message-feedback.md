# Message Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add thumbs-up / thumbs-down feedback modals to assistant messages, POSTing feedback to the local Python server.

**Architecture:** A new `FeedbackModal` React component handles both positive and negative feedback UI. `MessageBubble` manages open/close state and renders the modal. A new FastAPI router in `feedback.py` handles `POST /feedback`, logs the payload, and returns `{"ok": true}`.

**Tech Stack:** React + TypeScript (frontend), FastAPI + Pydantic (backend), existing design tokens in `index.css`.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `proteinclaw/server/feedback.py` | POST /feedback route + Pydantic model |
| Modify | `proteinclaw/server/main.py` | Include feedback router |
| Modify | `frontend/src/index.css` | Add `.feedback-modal` CSS classes |
| Create | `frontend/src/components/FeedbackModal.tsx` | Modal UI for positive and negative feedback |
| Modify | `frontend/src/components/MessageBubble.tsx` | Wire up ThumbsUp/ThumbsDown, render FeedbackModal |

---

## Task 1: Backend — `feedback.py` router

**Files:**
- Create: `proteinclaw/server/feedback.py`
- Create: `tests/server/test_feedback.py`

- [ ] **Step 1: Write the failing test**

Create `tests/server/test_feedback.py`:

```python
from fastapi.testclient import TestClient
from proteinclaw.server.main import app

client = TestClient(app)


def test_feedback_positive_returns_ok():
    resp = client.post("/feedback", json={
        "type": "positive",
        "category": None,
        "comment": "Very helpful!",
        "message_content": "The protein folding prediction was accurate."
    })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_feedback_negative_returns_ok():
    resp = client.post("/feedback", json={
        "type": "negative",
        "category": "Not factually correct",
        "comment": "The citation was wrong.",
        "message_content": "According to Smith et al. 2020..."
    })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_feedback_missing_type_returns_422():
    resp = client.post("/feedback", json={
        "comment": "some comment",
        "message_content": "some content"
    })
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Volumes/ExternalDisk/data/code/ProteinClaw
python -m pytest tests/server/test_feedback.py -v
```

Expected: `FAILED` — `404` because the route doesn't exist yet.

- [ ] **Step 3: Create `proteinclaw/server/feedback.py`**

```python
import logging
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    type: str                    # "positive" | "negative"
    category: Optional[str]      # error category, negative only
    comment: str
    message_content: str         # first 100 chars of the AI message


@router.post("/feedback")
async def submit_feedback(payload: FeedbackRequest):
    logger.info(
        "feedback received: type=%s category=%s comment=%r message_content=%r",
        payload.type,
        payload.category,
        payload.comment[:200] if payload.comment else "",
        payload.message_content[:100],
    )
    # TODO(future): forward to remote server here
    return {"ok": True}
```

- [ ] **Step 4: Include router in `main.py`**

Add these two lines to `proteinclaw/server/main.py`:

```python
from proteinclaw.server.feedback import router as feedback_router
# ... (after existing imports)
app.include_router(feedback_router)
```

Full updated `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from proteinclaw.server.tools import router as tools_router
from proteinclaw.server.chat import router as chat_router
from proteinclaw.server.feedback import router as feedback_router
from proteinclaw.core.config import load_user_config

load_user_config()

app = FastAPI(title="ProteinClaw", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(tools_router)
app.include_router(chat_router)
app.include_router(feedback_router)
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd /Volumes/ExternalDisk/data/code/ProteinClaw
python -m pytest tests/server/test_feedback.py -v
```

Expected output:
```
PASSED tests/server/test_feedback.py::test_feedback_positive_returns_ok
PASSED tests/server/test_feedback.py::test_feedback_negative_returns_ok
PASSED tests/server/test_feedback.py::test_feedback_missing_type_returns_422
```

- [ ] **Step 6: Commit**

```bash
git add proteinclaw/server/feedback.py proteinclaw/server/main.py tests/server/test_feedback.py
git commit -m "feat: add POST /feedback endpoint with logging"
```

---

## Task 2: Frontend CSS — feedback modal styles

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Add CSS classes**

Append the following block to the end of `frontend/src/index.css` (before the final `</style>` if any, otherwise just append):

```css
/* ── Feedback Modal ──────────────────────────────────────── */
.feedback-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.feedback-modal {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 420px;
  max-width: calc(100vw - 32px);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.16);
  z-index: 1001;
  display: flex;
  flex-direction: column;
}

.feedback-modal__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--border-light);
}

.feedback-modal__title {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  font-family: var(--display);
  color: var(--text-h);
  letter-spacing: -0.01em;
  margin: 0;
}

.feedback-modal__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: none;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: var(--text);
  flex-shrink: 0;
  transition: background 120ms, color 120ms;
}

.feedback-modal__close:hover {
  background: var(--border);
  color: var(--text-h);
}

.feedback-modal__body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feedback-modal__label {
  font-size: 13px;
  font-family: var(--sans);
  color: var(--text);
  margin: 0 0 4px;
}

.feedback-modal__select {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  font-size: 14px;
  font-family: var(--sans);
  outline: none;
  cursor: pointer;
  transition: border-color 150ms;
}

.feedback-modal__select:focus {
  border-color: var(--accent);
}

.feedback-modal__textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text-h);
  font-size: 14px;
  font-family: var(--sans);
  line-height: 1.5;
  resize: none;
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms;
}

.feedback-modal__textarea:focus {
  border-color: var(--accent);
}

.feedback-modal__textarea::placeholder {
  color: var(--text-xs);
}

.feedback-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 0 16px 16px;
}

.feedback-modal__cancel {
  padding: 7px 16px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 14px;
  font-family: var(--sans);
  color: var(--text-h);
  cursor: pointer;
  transition: background 120ms;
}

.feedback-modal__cancel:hover {
  background: var(--border);
}

.feedback-modal__submit {
  padding: 7px 16px;
  background: var(--accent);
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-family: var(--sans);
  color: #fff;
  cursor: pointer;
  transition: opacity 120ms;
}

.feedback-modal__submit:hover {
  opacity: 0.85;
}

.feedback-modal__submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
```

- [ ] **Step 2: Verify no syntax errors**

```bash
cd /Volumes/ExternalDisk/data/code/ProteinClaw/frontend
npx vite build --mode development 2>&1 | grep -i error | head -20
```

Expected: no CSS errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/index.css
git commit -m "feat: add feedback modal CSS"
```

---

## Task 3: Frontend — `FeedbackModal` component

**Files:**
- Create: `frontend/src/components/FeedbackModal.tsx`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/FeedbackModal.tsx`:

```tsx
import { useState } from "react";
import { X } from "lucide-react";

const NEGATIVE_CATEGORIES = [
  "UI bug",
  "Overactive refusal",
  "Poor image understanding",
  "Did not fully follow my request",
  "Not factually correct",
  "Incomplete response",
  "Should have searched the web",
  "Report content",
  "Not in keeping with Claude's Constitution",
  "Other",
];

interface Props {
  type: "positive" | "negative";
  messageContent: string;
  onClose: () => void;
}

export function FeedbackModal({ type, messageContent, onClose }: Props) {
  const [category, setCategory] = useState("");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isPositive = type === "positive";
  const canSubmit = isPositive ? true : category !== "";

  async function handleSubmit() {
    if (!canSubmit || submitting) return;
    setSubmitting(true);
    const port = (window as any).__BACKEND_PORT__ ?? 8000;
    try {
      await fetch(`http://127.0.0.1:${port}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type,
          category: isPositive ? null : category,
          comment,
          message_content: messageContent.slice(0, 100),
        }),
      });
    } catch (err) {
      console.warn("[FeedbackModal] failed to submit feedback:", err);
    }
    onClose();
  }

  return (
    <>
      <div className="feedback-overlay" onClick={onClose} />
      <div className="feedback-modal" role="dialog" aria-modal="true">
        <div className="feedback-modal__header">
          <h3 className="feedback-modal__title">
            {isPositive ? "👍 Positive Feedback" : "👎 Report an Issue"}
          </h3>
          <button
            className="feedback-modal__close"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} strokeWidth={1.8} />
          </button>
        </div>

        <div className="feedback-modal__body">
          {!isPositive && (
            <div>
              <p className="feedback-modal__label">What went wrong?</p>
              <select
                className="feedback-modal__select"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                autoFocus
              >
                <option value="">Select a category...</option>
                {NEGATIVE_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          )}

          <div>
            <p className="feedback-modal__label">
              {isPositive
                ? "What did you like about this response?"
                : "Additional details (optional)"}
            </p>
            <textarea
              className="feedback-modal__textarea"
              rows={3}
              placeholder={isPositive ? "Tell us what was helpful…" : "Describe the issue…"}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              autoFocus={isPositive}
            />
          </div>
        </div>

        <div className="feedback-modal__actions">
          <button className="feedback-modal__cancel" onClick={onClose}>
            Cancel
          </button>
          <button
            className="feedback-modal__submit"
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
          >
            {submitting ? "Sending…" : "Submit"}
          </button>
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Volumes/ExternalDisk/data/code/ProteinClaw/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/FeedbackModal.tsx
git commit -m "feat: add FeedbackModal component"
```

---

## Task 4: Frontend — wire up `MessageBubble`

**Files:**
- Modify: `frontend/src/components/MessageBubble.tsx`

- [ ] **Step 1: Update `MessageBubble.tsx`**

Replace the full file content with:

```tsx
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Copy, ThumbsUp, ThumbsDown, RotateCcw, Check } from "lucide-react";
import type { Message } from "../types";
import { ToolCallCard } from "./ToolCallCard";
import { ClaudeLogo } from "./ClaudeLogo";
import { FeedbackModal } from "./FeedbackModal";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const [copied, setCopied] = useState(false);
  const [feedbackModal, setFeedbackModal] = useState<"positive" | "negative" | null>(null);

  const calls = message.toolCalls?.filter((e) => e.type === "tool_call") ?? [];
  const obs = message.toolCalls?.filter((e) => e.type === "observation") ?? [];

  function handleCopy() {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  if (message.role === "user") {
    return (
      <div className="msg-user-wrap">
        <div className="msg-user-bubble">{message.content}</div>
      </div>
    );
  }

  return (
    <div className="msg-assistant-wrap">
      <div className="msg-assistant-logo">
        <ClaudeLogo size={20} />
      </div>
      <div className="msg-assistant-body">
        {calls.map((tc, j) => (
          <ToolCallCard key={j} toolCall={tc} observation={obs[j]} />
        ))}
        <div className="msg-assistant-content">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        {message.content && (
          <div className="msg-reactions">
            <button className="msg-reaction-btn" onClick={handleCopy} title="Copy" aria-label={copied ? "Copied" : "Copy response"}>
              {copied ? <Check size={14} strokeWidth={2} /> : <Copy size={14} strokeWidth={1.8} />}
            </button>
            <button
              className="msg-reaction-btn"
              title="Good response"
              aria-label="Mark as helpful"
              onClick={() => setFeedbackModal("positive")}
            >
              <ThumbsUp size={14} strokeWidth={1.8} />
            </button>
            <button
              className="msg-reaction-btn"
              title="Bad response"
              aria-label="Mark as unhelpful"
              onClick={() => setFeedbackModal("negative")}
            >
              <ThumbsDown size={14} strokeWidth={1.8} />
            </button>
            <button className="msg-reaction-btn" title="Retry" aria-label="Regenerate response">
              <RotateCcw size={14} strokeWidth={1.8} />
            </button>
          </div>
        )}
      </div>

      {feedbackModal && (
        <FeedbackModal
          type={feedbackModal}
          messageContent={message.content}
          onClose={() => setFeedbackModal(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Volumes/ExternalDisk/data/code/ProteinClaw/frontend
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 3: Manual smoke test**

Start the dev server and verify:
1. An assistant message appears in a chat
2. Click 👍 → "Positive Feedback" modal opens, textarea is focused
3. Type some text, click Submit → modal closes, no JS error in console
4. Click 👎 → "Report an Issue" modal opens, dropdown is focused
5. Submit is disabled until a category is selected
6. Select "Not factually correct", click Submit → modal closes
7. Click overlay behind either modal → modal closes
8. Check backend log for `feedback received:` entries

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/MessageBubble.tsx
git commit -m "feat: wire feedback modals into MessageBubble"
```
