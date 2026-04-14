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
    const controller = new AbortController();
    const port = (window as any).__BACKEND_PORT__ || 8000;
    fetch(`http://localhost:${port}/api/case-studies`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setCases(data.cases ?? []);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, []);

  return { cases, loading, error };
}
