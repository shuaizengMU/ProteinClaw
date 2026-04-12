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
      const resp = await fetch(`http://127.0.0.1:${port}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          feedback_type: type,
          category: isPositive ? null : category,
          comment,
          message_content: messageContent.slice(0, 100),
        }),
      });
      if (!resp.ok) {
        console.warn("[FeedbackModal] feedback returned non-ok status:", resp.status);
      }
    } catch (err) {
      console.warn("[FeedbackModal] failed to submit feedback:", err);
    } finally {
      setSubmitting(false);
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
