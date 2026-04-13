import type { CaseStudyCategory } from "../types";

export const CATEGORIES: CaseStudyCategory[] = [
  { id: "all",      label: "All",              color: "#888" },
  { id: "sequence", label: "Sequence Analysis", color: "#60a5fa" },
  { id: "structure",label: "Structure",         color: "#a78bfa" },
  { id: "drug",     label: "Drug Discovery",    color: "#34d399" },
  { id: "function",   label: "Function",             color: "#fb923c" },
  { id: "annotation", label: "Annotation",           color: "#f59e0b" },
  { id: "variants",   label: "Variants & Clinical",  color: "#ec4899" },
  { id: "disease",    label: "Disease & Oncology",   color: "#ef4444" },
  { id: "pathways",   label: "Pathways & Networks",  color: "#06b6d4" },
  { id: "expression", label: "Expression",           color: "#84cc16" },
  { id: "genomics",   label: "Gene & Genomics",      color: "#8b5cf6" },
  { id: "literature", label: "Literature",           color: "#94a3b8" },
];

interface Props {
  activeCategoryId: string;
  counts: Record<string, number>;
  onSelect: (id: string) => void;
}

export function CaseStudyCategoryNav({ activeCategoryId, counts, onSelect }: Props) {
  return (
    <nav className="cs-cat-nav" aria-label="Case study categories">
      <div className="cs-cat-nav__label">Categories</div>
      {CATEGORIES.map((cat) => (
        <button
          key={cat.id}
          type="button"
          className={`cs-cat-item${activeCategoryId === cat.id ? " cs-cat-item--active" : ""}`}
          onClick={() => onSelect(cat.id)}
          aria-current={activeCategoryId === cat.id ? "page" : undefined}
        >
          <span className="cs-cat-item__dot" style={{ background: cat.color }} />
          <span className="cs-cat-item__label">{cat.label}</span>
          <span className="cs-cat-item__count">{counts[cat.id] ?? 0}</span>
        </button>
      ))}
    </nav>
  );
}
