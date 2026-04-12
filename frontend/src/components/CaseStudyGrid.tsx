import { CaseStudyCard } from "./CaseStudyCard";
import { CATEGORIES } from "./CaseStudyCategoryNav";
import type { CaseStudy } from "../types";

interface Props {
  cases: CaseStudy[];
  activeCategoryId: string;
  onCardClick: (c: CaseStudy) => void;
}

export function CaseStudyGrid({ cases, activeCategoryId, onCardClick }: Props) {
  const visibleCategories = activeCategoryId === "all"
    ? CATEGORIES.filter((c) => c.id !== "all")
    : CATEGORIES.filter((c) => c.id === activeCategoryId);

  return (
    <main className="cs-main">
      <div className="cs-main__header">
        <h2 className="cs-main__title">Case Studies</h2>
        <p className="cs-main__subtitle">Click any card to see details and try it</p>
      </div>

      {visibleCategories.map((cat) => {
        const group = cases.filter((c) => c.category === cat.id);
        if (group.length === 0) return null;
        return (
          <section key={cat.id}>
            <div className="cs-section-label">{cat.label}</div>
            <div className="cs-card-grid">
              {group.map((c) => (
                <CaseStudyCard key={c.id} caseStudy={c} onClick={onCardClick} />
              ))}
            </div>
          </section>
        );
      })}
    </main>
  );
}
