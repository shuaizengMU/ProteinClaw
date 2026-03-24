import { useState } from "react";
import { WsEvent } from "../types";

interface Props {
  toolCall: WsEvent;
  observation?: WsEvent;
}

export function ToolCallCard({ toolCall, observation }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div
      style={{
        border: "1px solid #ccc",
        borderRadius: 6,
        margin: "4px 0",
        fontSize: 13,
        background: "#f9f9f9",
      }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          width: "100%",
          textAlign: "left",
          padding: "6px 10px",
          background: "none",
          border: "none",
          cursor: "pointer",
          fontWeight: 500,
        }}
      >
        {open ? "▼" : "▶"} Tool: <code>{toolCall.tool}</code>
        {observation && (observation.result as any)?.success === false && (
          <span style={{ color: "red", marginLeft: 8 }}>✗ failed</span>
        )}
        {observation && (observation.result as any)?.success === true && (
          <span style={{ color: "green", marginLeft: 8 }}>✓</span>
        )}
      </button>
      {open && (
        <div style={{ padding: "0 10px 8px", borderTop: "1px solid #eee" }}>
          <div style={{ marginTop: 6 }}>
            <strong>Args:</strong>
            <pre style={{ margin: "4px 0", overflowX: "auto" }}>
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>
          {observation && (
            <div style={{ marginTop: 6 }}>
              <strong>Result:</strong>
              <pre style={{ margin: "4px 0", overflowX: "auto" }}>
                {JSON.stringify(observation.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
