import { useState } from "react";
import { useCaseStudies } from "../hooks/useCaseStudies";
import { CaseStudyCategoryNav, CATEGORIES } from "./CaseStudyCategoryNav";
import { CaseStudyGrid } from "./CaseStudyGrid";
import { CaseStudyModal } from "./CaseStudyModal";
import type { CaseStudy } from "../types";

interface Props {
  onTryIt: (prompt: string) => void;
}

export function CaseStudyPage({ onTryIt }: Props) {
  const { cases, loading, error } = useCaseStudies();
  const [activeCategoryId, setActiveCategoryId] = useState<string>("all");
  const [selectedCase, setSelectedCase] = useState<CaseStudy | null>(null);

  const counts: Record<string, number> = { all: cases.length };
  CATEGORIES.forEach((cat) => {
    if (cat.id !== "all") {
      counts[cat.id] = cases.filter((c) => c.category === cat.id).length;
    }
  });

  if (loading) {
    return (
      <div className="cs-page cs-page--loading">
        <span className="cs-page__loading-text">Loading case studies…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="cs-page cs-page--error">
        <span className="cs-page__error-text">Failed to load case studies: {error}</span>
      </div>
    );
  }

  return (
    <div className="cs-page">
      <CaseStudyCategoryNav
        activeCategoryId={activeCategoryId}
        counts={counts}
        onSelect={setActiveCategoryId}
      />
      <CaseStudyGrid
        cases={cases}
        activeCategoryId={activeCategoryId}
        onCardClick={setSelectedCase}
      />
      {selectedCase && (
        <CaseStudyModal
          caseStudy={selectedCase}
          onClose={() => setSelectedCase(null)}
          onTryIt={(prompt) => {
            setSelectedCase(null);
            onTryIt(prompt);
          }}
        />
      )}
    </div>
  );
}
