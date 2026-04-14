import { useState } from "react";

const STORAGE_KEY = "proteinclaw_model";

export function useStoredModel(): [string, (m: string) => void] {
  const [model, setModel] = useState(
    () => localStorage.getItem(STORAGE_KEY) ?? ""
  );

  const setStoredModel = (m: string) => {
    setModel(m);
    localStorage.setItem(STORAGE_KEY, m);
  };

  return [model, setStoredModel];
}
