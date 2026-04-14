import { useState, useEffect } from "react";
import { ArrowLeft } from "lucide-react";

const PROVIDERS = [
  { label: "Anthropic", storageKey: "ANTHROPIC_API_KEY", comingSoon: false },
  { label: "OpenAI",    storageKey: "OPENAI_API_KEY", comingSoon: false },
  { label: "DeepSeek",  storageKey: "DEEPSEEK_API_KEY", comingSoon: false },
  { label: "Google",    storageKey: "GEMINI_API_KEY", comingSoon: true },
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
  const [savedKeys, setSavedKeys] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      PROVIDERS.map(({ storageKey }) => [storageKey, localStorage.getItem(storageKey) ?? ""])
    )
  );

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  function handleFocus(storageKey: string) {
    setEditing(storageKey);
    setEditValue(savedKeys[storageKey] ?? "");
  }

  function handleBlur(storageKey: string) {
    const trimmed = editValue.trim();
    if (trimmed) {
      localStorage.setItem(storageKey, trimmed);
    } else {
      localStorage.removeItem(storageKey);
    }
    setSavedKeys((prev) => ({ ...prev, [storageKey]: trimmed }));
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
        {PROVIDERS.map(({ label, storageKey, comingSoon }) => {
          const isEditing = editing === storageKey;
          return (
            <div key={storageKey} className="api-keys-provider">
              <label
                className="api-keys-provider-label"
                htmlFor={`api-key-input-${storageKey}`}
              >
                {label}
                {comingSoon && (
                  <span className="api-keys-coming-soon">coming soon</span>
                )}
              </label>
              <input
                id={`api-key-input-${storageKey}`}
                className="api-keys-provider-input"
                type="text"
                value={isEditing ? editValue : maskKey(savedKeys[storageKey] ?? "")}
                placeholder="Click to enter..."
                readOnly={!isEditing}
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
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
