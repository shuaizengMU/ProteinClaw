import { useState, useEffect } from "react";
import type { CaseStudy } from "../types";

interface UseCaseStudiesResult {
  cases: CaseStudy[];
  loading: boolean;
  error: string | null;
}

export function useCaseStudies(): UseCaseStudiesResult {
  const [cases, setCases] = useState<CaseStudy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const port = (window as any).__BACKEND_PORT__ || 8000;
    fetch(`http://localhost:${port}/api/case-studies`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setCases(data.cases ?? []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return { cases, loading, error };
}
