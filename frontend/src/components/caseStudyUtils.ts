import {
  Dna, Search, BarChart2, GitBranch, Layers, Box,
  FlaskConical, Activity, BookOpen,
} from "lucide-react";

export const CASE_ICON_MAP: Record<string, React.FC<{ size?: number; strokeWidth?: number }>> = {
  dna: Dna,
  search: Search,
  "bar-chart": BarChart2,
  "git-branch": GitBranch,
  layers: Layers,
  box: Box,
  flask: FlaskConical,
  activity: Activity,
};

export const CASE_CATEGORY_COLORS: Record<string, string> = {
  sequence: "#60a5fa",
  structure: "#a78bfa",
  drug: "#34d399",
  function: "#fb923c",
};

export const CASE_CATEGORY_LABELS: Record<string, string> = {
  sequence: "Sequence Analysis",
  structure: "Structure",
  drug: "Drug Discovery",
  function: "Function",
};

export function getCaseIcon(icon: string) {
  return CASE_ICON_MAP[icon] ?? BookOpen;
}
