import { useEffect } from "react";
import { X, ChevronRight, Dna, Search, BarChart2, GitBranch, Layers, Box, FlaskConical, Activity, BookOpen } from "lucide-react";
import type { CaseStudy } from "../types";

const ICON_MAP: Record<string, React.FC<{ size?: number; strokeWidth?: number }>> = {
  dna: Dna, search: Search, "bar-chart": BarChart2, "git-branch": GitBranch,
  layers: Layers, box: Box, flask: FlaskConical, activity: Activity,
};

const CATEGORY_COLORS: Record<string, string> = {
  sequence: "#60a5fa", structure: "#a78bfa", drug: "#34d399", function: "#fb923c",
};

const CATEGORY_LABELS: Record<string, string> = {
  sequence: "Sequence Analysis", structure: "Structure",
  drug: "Drug Discovery", function: "Function",
};

interface Props {
  caseStudy: CaseStudy;
  onClose: () => void;
  onTryIt: (prompt: string) => void;
}

export function CaseStudyModal({ caseStudy, onClose, onTryIt }: Props) {
  const Icon = ICON_MAP[caseStudy.icon] ?? BookOpen;
  const color = CATEGORY_COLORS[caseStudy.category] ?? "#aaa";

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
        className="cs-modal"
        role="dialog"
        aria-modal="true"
        aria-label={caseStudy.title}
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
            <div className="cs-modal__title">{caseStudy.title}</div>
            <div className="cs-modal__category" style={{ color, background: `${color}1a` }}>
              {CATEGORY_LABELS[caseStudy.category] ?? caseStudy.category}
            </div>
          </div>
          <button className="cs-modal__close" onClick={onClose} aria-label="Close">
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
          <button className="cs-modal__btn-secondary" onClick={onClose}>
            Close
          </button>
          <button
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
