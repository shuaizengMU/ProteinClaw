import { useState } from "react";

const STORAGE_KEY = "proteinclaw_model";

export function useStoredModel(): [string, (m: string) => void] {
  const [model, setModel] = useState(
    () => localStorage.getItem(STORAGE_KEY) ?? "gpt-4o"
  );
  return [model, setModel];
}
