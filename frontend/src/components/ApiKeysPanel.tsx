import { useState, useEffect } from "react";
import { ArrowLeft } from "lucide-react";

const PROVIDERS = [
  { label: "Anthropic", storageKey: "ANTHROPIC_API_KEY" },
  { label: "OpenAI",    storageKey: "OPENAI_API_KEY" },
  { label: "DeepSeek",  storageKey: "DEEPSEEK_API_KEY" },
  { label: "Google",    storageKey: "GEMINI_API_KEY" },
] as const;

function maskKey(value: string): string {
  if (!value) return "";
  if (value.length <= 6) return "••••••";
  return value.slice(0, 6) + "••••••••";
}

interface Props {
  onClose: () => void;
}

export function ApiKeysPanel({ onClose }: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  function handleFocus(storageKey: string) {
    setEditing(storageKey);
    setEditValue(localStorage.getItem(storageKey) ?? "");
  }

  function handleBlur(storageKey: string) {
    const trimmed = editValue.trim();
    if (trimmed) {
      localStorage.setItem(storageKey, trimmed);
    } else {
      localStorage.removeItem(storageKey);
    }
    setEditing(null);
    setEditValue("");
  }

  return (
    <div className="api-keys-panel">
      <div className="api-keys-panel-header">
        <button
          className="api-keys-panel-back"
          onClick={onClose}
          aria-label="Close API Keys panel"
        >
          <ArrowLeft size={15} strokeWidth={1.8} />
        </button>
        <span className="api-keys-panel-title">API Keys</span>
      </div>

      <div className="api-keys-panel-body">
        {PROVIDERS.map(({ label, storageKey }) => {
          const saved = localStorage.getItem(storageKey) ?? "";
          const isEditing = editing === storageKey;
          return (
            <div key={storageKey} className="api-keys-provider">
              <label className="api-keys-provider-label">{label}</label>
              <input
                className="api-keys-provider-input"
                type="text"
                value={isEditing ? editValue : maskKey(saved)}
                placeholder="点击输入..."
                readOnly={!isEditing}
                onFocus={() => handleFocus(storageKey)}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={() => handleBlur(storageKey)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
