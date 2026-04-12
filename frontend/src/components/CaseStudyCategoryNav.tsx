import type { CaseStudyCategory } from "../types";

export const CATEGORIES: CaseStudyCategory[] = [
  { id: "all",      label: "All",              color: "#888" },
  { id: "sequence", label: "Sequence Analysis", color: "#60a5fa" },
  { id: "structure",label: "Structure",         color: "#a78bfa" },
  { id: "drug",     label: "Drug Discovery",    color: "#34d399" },
  { id: "function", label: "Function",          color: "#fb923c" },
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
