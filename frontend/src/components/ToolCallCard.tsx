import { useState } from "react";
import type { WsEvent } from "../types";

interface Props {
  toolCall: WsEvent;
  observation?: WsEvent;
}

export function ToolCallCard({ toolCall, observation }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <div className="tool-call-card">
      <button
        className="tool-call-card__header"
        onClick={() => setOpen((o) => !o)}
      >
        <span>{open ? "▼" : "▶"}</span>
        <span>
          Tool: <code>{toolCall.tool}</code>
        </span>
        {observation?.result?.["success"] === false && (
          <span className="tool-call-status--err">✗ failed</span>
        )}
        {observation?.result?.["success"] === true && (
          <span className="tool-call-status--ok">✓</span>
        )}
      </button>
      {open && (
        <div className="tool-call-card__body">
          <strong>Args:</strong>
          <pre>{JSON.stringify(toolCall.args, null, 2)}</pre>
          {observation && (
            <>
              <strong>Result:</strong>
              <pre>{JSON.stringify(observation.result, null, 2)}</pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}
