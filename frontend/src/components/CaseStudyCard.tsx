import {
  Dna, Search, BarChart2, GitBranch, Layers, Box,
  FlaskConical, Activity, BookOpen, ChevronRight,
} from "lucide-react";
import type { CaseStudy } from "../types";

const ICON_MAP: Record<string, React.FC<{ size?: number; strokeWidth?: number }>> = {
  dna: Dna,
  search: Search,
  "bar-chart": BarChart2,
  "git-branch": GitBranch,
  layers: Layers,
  box: Box,
  flask: FlaskConical,
  activity: Activity,
};

const CATEGORY_COLORS: Record<string, string> = {
  sequence: "#60a5fa",
  structure: "#a78bfa",
  drug: "#34d399",
  function: "#fb923c",
};

function CaseIcon({ icon, category }: { icon: string; category: string }) {
  const Icon = ICON_MAP[icon] ?? BookOpen;
  const color = CATEGORY_COLORS[category] ?? "#aaa";
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
      onKeyDown={(e) => e.key === "Enter" && onClick(caseStudy)}
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
