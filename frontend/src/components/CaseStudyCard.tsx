import { ChevronRight } from "lucide-react";
import type { CaseStudy } from "../types";
import { getCaseIcon, CASE_CATEGORY_COLORS } from "./caseStudyUtils";

function CaseIcon({ icon, category }: { icon: string; category: string }) {
  const Icon = getCaseIcon(icon);
  const color = CASE_CATEGORY_COLORS[category] ?? "#aaa";
  return (
    <div
      className="cs-card__icon"
      style={{
        background: `${color}1a`,
        color,
      }}
    >
      <Icon size={17} strokeWidth={1.8} />
    </div>
  );
}

interface Props {
  caseStudy: CaseStudy;
  onClick: (c: CaseStudy) => void;
}

export function CaseStudyCard({ caseStudy, onClick }: Props) {
  return (
    <div
      className="cs-card"
      onClick={() => onClick(caseStudy)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick(caseStudy);
        }
      }}
      aria-label={`Open case study: ${caseStudy.title}`}
    >
      <CaseIcon icon={caseStudy.icon} category={caseStudy.category} />
      <div className="cs-card__body">
        <div className="cs-card__title">{caseStudy.title}</div>
        <div className="cs-card__desc">{caseStudy.description}</div>
      </div>
      <div className="cs-card__action" aria-hidden="true">
        <ChevronRight size={13} strokeWidth={2} />
      </div>
    </div>
  );
}
