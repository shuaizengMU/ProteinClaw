import { useEffect, useRef } from "react";
import { X, ChevronRight } from "lucide-react";
import type { CaseStudy } from "../types";
import { getCaseIcon, CASE_CATEGORY_COLORS, CASE_CATEGORY_LABELS } from "./caseStudyUtils";

interface Props {
  caseStudy: CaseStudy;
  onClose: () => void;
  onTryIt: (prompt: string) => void;
}

export function CaseStudyModal({ caseStudy, onClose, onTryIt }: Props) {
  const Icon = getCaseIcon(caseStudy.icon);
  const color = CASE_CATEGORY_COLORS[caseStudy.category] ?? "#aaa";
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    modalRef.current?.focus();
  }, []);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <>
      <div className="cs-modal-backdrop" onClick={onClose} aria-hidden="true" />
      <div
        ref={modalRef}
        tabIndex={-1}
        className="cs-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cs-modal-title"
      >
        {/* Header */}
        <div className="cs-modal__header">
          <div
            className="cs-modal__icon"
            style={{ background: `${color}1a`, color }}
          >
            <Icon size={20} strokeWidth={1.8} />
          </div>
          <div className="cs-modal__title-block">
            <div id="cs-modal-title" className="cs-modal__title">{caseStudy.title}</div>
            <div className="cs-modal__category" style={{ color, background: `${color}1a` }}>
              {CASE_CATEGORY_LABELS[caseStudy.category] ?? caseStudy.category}
            </div>
          </div>
          <button type="button" className="cs-modal__close" onClick={onClose} aria-label="Close">
            <X size={15} strokeWidth={2} />
          </button>
        </div>

        {/* Body */}
        <div className="cs-modal__body">
          <p className="cs-modal__desc">{caseStudy.description}</p>

          <div className="cs-modal__section">
            <div className="cs-modal__block-label">Example Prompt</div>
            <pre className="cs-modal__code">{caseStudy.examplePrompt}</pre>
          </div>

          <div className="cs-modal__section">
            <div className="cs-modal__block-label">Example Result</div>
            <pre className="cs-modal__result">{caseStudy.exampleResult}</pre>
          </div>
        </div>

        {/* Footer */}
        <div className="cs-modal__footer">
          <button type="button" className="cs-modal__btn-secondary" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="cs-modal__btn-primary"
            onClick={() => onTryIt(caseStudy.examplePrompt)}
          >
            <ChevronRight size={13} strokeWidth={2} />
            Try it
          </button>
        </div>
      </div>
    </>
  );
}
