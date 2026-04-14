# Message Feedback Design

**Date:** 2026-04-12
**Status:** Approved

## Overview

Add thumbs-up / thumbs-down feedback modals to each assistant message in the chat window. Positive feedback shows a free-text input; negative feedback shows an error category dropdown plus a free-text input. Feedback is POSTed to the local Python server, which logs it and is designed to forward to a remote server in the future.

---

## Component Architecture

### New file: `frontend/src/components/FeedbackModal.tsx`

```
props:
  type: 'positive' | 'negative'
  messageContent: string        // first 100 chars of the AI message, sent to backend
  onClose: () => void
```

Internal state:
- `comment: string` — textarea value
- `category: string` — selected dropdown value (negative only), default `""`
- `submitting: boolean` — prevents double-submit

### Changes to `MessageBubble.tsx`

- Add state: `feedbackModal: 'positive' | 'negative' | null`
- ThumbsUp click → `setFeedbackModal('positive')`
- ThumbsDown click → `setFeedbackModal('negative')`
- Render at JSX end: `{feedbackModal && <FeedbackModal type={feedbackModal} messageContent={...} onClose={() => setFeedbackModal(null)} />}`

---

## Data Flow

### Request

```
POST http://127.0.0.1:{port}/feedback
Content-Type: application/json

{
  "type": "positive" | "negative",
  "category": "Not factually correct" | null,
  "comment": "user input text",
  "message_content": "<first 100 chars of AI message>"
}
```

### Backend (`proteinclaw/server/main.py`)

- Add `POST /feedback` route
- Log the payload via `logger.info`
- Return `{"ok": true}`
- Interface designed for easy future replacement with remote server forwarding

### Error handling

- If POST fails, log a `console.warn` in the frontend; modal closes normally
- No UI error state shown to user (non-critical)

---

## UI / UX

### Positive Feedback Modal

```
┌─────────────────────────────────┐
│ 👍 Positive Feedback        [X] │
├─────────────────────────────────┤
│ What did you like about this    │
│ response?                       │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ (textarea, 3 rows)          │ │
│ └─────────────────────────────┘ │
│                                 │
│              [Cancel] [Submit]  │
└─────────────────────────────────┘
```

- Submit enabled even with empty comment

### Negative Feedback Modal

```
┌─────────────────────────────────┐
│ 👎 Report an Issue          [X] │
├─────────────────────────────────┤
│ What went wrong?                │
│ ┌─────────────────────────────┐ │
│ │ Select a category...      ▼ │ │
│ └─────────────────────────────┘ │
│                                 │
│ Additional details (optional)   │
│ ┌─────────────────────────────┐ │
│ │ (textarea, 3 rows)          │ │
│ └─────────────────────────────┘ │
│                                 │
│              [Cancel] [Submit]  │
└─────────────────────────────────┘
```

- Submit **disabled** until a category is selected

### Error categories (negative)

1. UI bug
2. Overactive refusal
3. Poor image understanding
4. Did not fully follow my request
5. Not factually correct
6. Incomplete response
7. Should have searched the web
8. Report content
9. Not in keeping with Claude's Constitution
10. Other

### Common behaviour

- Modal: `position: fixed`, centered, `width: 420px`
- Background: semi-transparent overlay (`rgba(0,0,0,0.5)`)
- Click overlay → close modal (same as Cancel)
- After submit: POST fires, modal closes; button state unchanged

---

## CSS

New classes in `index.css`, all using existing design tokens:

| Class | Purpose |
|---|---|
| `.feedback-overlay` | Full-screen mask, `z-index: 1000` |
| `.feedback-modal` | White card, centered, `z-index: 1001` |
| `.feedback-modal__header` | Title row + close button |
| `.feedback-modal__title` | `font-family: var(--display)` |
| `.feedback-modal__close` | X button, same style as `right-sidebar__close` |
| `.feedback-modal__body` | Padded content area |
| `.feedback-modal__label` | Small label above inputs |
| `.feedback-modal__select` | Dropdown, full width |
| `.feedback-modal__textarea` | Textarea, full width, 3 rows |
| `.feedback-modal__actions` | Right-aligned button row |
| `.feedback-modal__cancel` | Secondary button |
| `.feedback-modal__submit` | Primary button, `var(--accent)`, disabled → lower opacity |

---

## Files Changed

| File | Change |
|---|---|
| `frontend/src/components/FeedbackModal.tsx` | **New** — modal component |
| `frontend/src/components/MessageBubble.tsx` | Add `feedbackModal` state, wire up buttons, render modal |
| `frontend/src/index.css` | Add `.feedback-modal` and related classes |
| `proteinclaw/server/main.py` | Add `POST /feedback` route |
