const MODELS = [
  "gpt-4o",
  "claude-opus-4-5",
  "deepseek-chat",
  "deepseek-reasoner",
  "minimax-text-01",
  "ollama/llama3",
];

const STORAGE_KEY = "proteinclaw_model";

interface Props {
  value: string;
  onChange: (model: string) => void;
}

export function ModelSelector({ value, onChange }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => {
        localStorage.setItem(STORAGE_KEY, e.target.value);
        onChange(e.target.value);
      }}
      style={{ marginLeft: "auto", padding: "4px 8px" }}
    >
      {MODELS.map((m) => (
        <option key={m} value={m}>
          {m}
        </option>
      ))}
    </select>
  );
}
