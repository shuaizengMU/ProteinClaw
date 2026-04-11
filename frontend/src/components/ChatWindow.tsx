import { useState, useRef, useEffect } from "react";
import { Plus, Mic, Share2, ChevronDown, ArrowUp, Menu, Pin, PencilLine, Trash2 } from "lucide-react";
import type { Message } from "../types";
import { MessageBubble } from "./MessageBubble";
import { ClaudeLogo } from "./ClaudeLogo";

const MODELS = [
  "claude-opus-4-5",
  "claude-sonnet-4-6",
  "gpt-4o",
  "deepseek-chat",
  "deepseek-reasoner",
  "ollama/llama3",
];

const MODEL_CONFIG_KEYS: Record<string, string> = {
  "claude-opus-4-5": "ANTHROPIC_API_KEY",
  "claude-sonnet-4-6": "ANTHROPIC_API_KEY",
  "gpt-4o": "OPENAI_API_KEY",
  "deepseek-chat": "DEEPSEEK_API_KEY",
  "deepseek-reasoner": "DEEPSEEK_API_KEY",
  "ollama/llama3": "OLLAMA_BASE_URL",
};

interface Props {
  messages: Message[];
  loading: boolean;
  title: string;
  model: string;
  onModelChange: (m: string) => void;
  onSend: (text: string) => void;
  hasConversation: boolean;
  onMenuToggle?: () => void;
  isPinned?: boolean;
  onPin?: () => void;
  onRename?: (newTitle: string) => void;
  onDelete?: () => void;
}

export function ChatWindow({
  messages,
  loading,
  title,
  model,
  onModelChange,
  onSend,
  hasConversation,
  onMenuToggle,
  isPinned,
  onPin,
  onRename,
  onDelete,
}: Props) {
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null);
  const [renameInput, setRenameInput] = useState(title);
  const [isRenaming, setIsRenaming] = useState(false);
  const [showModelConfig, setShowModelConfig] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [configValue, setConfigValue] = useState("");

  const handleContextMenu = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  // Close context menu when clicking elsewhere
  useEffect(() => {
    const handleClickOutside = () => setContextMenu(null);
    if (contextMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [contextMenu]);

  const handleRename = () => {
    if (renameInput.trim() && renameInput !== title) {
      onRename?.(renameInput.trim());
    }
    setIsRenaming(false);
    setContextMenu(null);
  };

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this chat?')) {
      onDelete?.();
    }
    setContextMenu(null);
  };

  if (!hasConversation) {
    return (
      <div className="chat-window chat-window--empty">
        <div className="empty-state">
          <ClaudeLogo size={40} />
          <h2>How can I help you?</h2>
          <p>Create a new chat from the sidebar.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-window" onContextMenu={handleContextMenu}>
      <TopBar title={title} onMenuToggle={onMenuToggle} />
      <MessageList messages={messages} loading={loading} />
      <InputArea onSend={onSend} loading={loading} model={model} onModelChange={onModelChange} />

      {/* Context Menu */}
      {contextMenu && (
        <>
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 998,
            }}
          />
          <div
            style={{
              position: 'fixed',
              top: `${contextMenu.y}px`,
              left: `${contextMenu.x}px`,
              zIndex: 999,
            }}
            className="sidebar-project-menu"
            onClick={(e) => e.stopPropagation()}
            onContextMenu={(e) => e.preventDefault()}
          >
            <button
              className="sidebar-menu-item"
              onClick={(e) => {
                e.stopPropagation();
                onPin?.();
                setContextMenu(null);
              }}
            >
              <Pin size={14} strokeWidth={1.8} />
              <span>{isPinned ? 'Unpin' : 'Pin'} Chat</span>
            </button>
            <button
              className="sidebar-menu-item"
              onClick={(e) => {
                e.stopPropagation();
                setIsRenaming(true);
                setContextMenu(null);
              }}
            >
              <PencilLine size={14} strokeWidth={1.8} />
              <span>Rename Chat</span>
            </button>
            <button
              className="sidebar-menu-item sidebar-menu-item--danger"
              onClick={(e) => {
                e.stopPropagation();
                handleDelete();
              }}
            >
              <Trash2 size={14} strokeWidth={1.8} />
              <span>Delete Chat</span>
            </button>
          </div>
        </>
      )}

      {/* Rename Dialog */}
      {isRenaming && (
        <>
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              zIndex: 999,
            }}
            onClick={() => setIsRenaming(false)}
          />
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '20px',
              zIndex: 1000,
              minWidth: '300px',
            }}
          >
            <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', fontFamily: 'var(--display)' }}>Rename Chat</h3>
            <input
              type="text"
              value={renameInput}
              onChange={(e) => setRenameInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRename();
                if (e.key === 'Escape') setIsRenaming(false);
              }}
              autoFocus
              style={{
                width: '100%',
                padding: '8px 12px',
                marginBottom: '12px',
                border: '1px solid var(--border)',
                borderRadius: '4px',
                fontSize: '14px',
                fontFamily: 'var(--sans)',
                backgroundColor: 'var(--bg)',
                color: 'var(--text-h)',
                boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setIsRenaming(false)}
                style={{
                  padding: '8px 16px',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  backgroundColor: 'var(--bg)',
                  color: 'var(--text-h)',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontFamily: 'var(--sans)',
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleRename}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderRadius: '4px',
                  backgroundColor: 'var(--accent)',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontFamily: 'var(--sans)',
                }}
              >
                Rename
              </button>
            </div>
          </div>
        </>
      )}

      {/* Model Config Dialog */}
      {showModelConfig && selectedModel && (
        <>
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              zIndex: 999,
            }}
            onClick={() => setShowModelConfig(false)}
          />
          <div
            style={{
              position: 'fixed',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              padding: '20px',
              zIndex: 1000,
              minWidth: '400px',
            }}
          >
            <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', fontFamily: 'var(--display)' }}>
              Configure {selectedModel.split("/").pop()}
            </h3>
            <p style={{ margin: '0 0 12px 0', fontSize: '14px', color: 'var(--text)', lineHeight: '1.5' }}>
              Please provide the required configuration for this model:
            </p>
            <input
              type="password"
              placeholder={MODEL_CONFIG_KEYS[selectedModel] || "Configuration value"}
              value={configValue}
              onChange={(e) => setConfigValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && configValue.trim()) {
                  localStorage.setItem(MODEL_CONFIG_KEYS[selectedModel], configValue);
                  onModelChange(selectedModel);
                  setShowModelConfig(false);
                }
              }}
              autoFocus
              style={{
                width: '100%',
                padding: '8px 12px',
                marginBottom: '12px',
                border: '1px solid var(--border)',
                borderRadius: '4px',
                fontSize: '14px',
                fontFamily: 'var(--sans)',
                backgroundColor: 'var(--bg)',
                color: 'var(--text-h)',
                boxSizing: 'border-box',
              }}
            />
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowModelConfig(false)}
                style={{
                  padding: '8px 16px',
                  border: '1px solid var(--border)',
                  borderRadius: '4px',
                  backgroundColor: 'var(--bg)',
                  color: 'var(--text-h)',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontFamily: 'var(--sans)',
                }}
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (configValue.trim()) {
                    localStorage.setItem(MODEL_CONFIG_KEYS[selectedModel], configValue);
                    onModelChange(selectedModel);
                    setShowModelConfig(false);
                  }
                }}
                disabled={!configValue.trim()}
                style={{
                  padding: '8px 16px',
                  border: 'none',
                  borderRadius: '4px',
                  backgroundColor: configValue.trim() ? 'var(--accent)' : 'var(--border)',
                  color: '#fff',
                  cursor: configValue.trim() ? 'pointer' : 'not-allowed',
                  fontSize: '14px',
                  fontFamily: 'var(--sans)',
                }}
              >
                Save
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function TopBar({ title, onMenuToggle }: { title: string; onMenuToggle?: () => void }) {
  return (
    <div className="top-bar">
      <button className="mobile-menu-btn" onClick={onMenuToggle} aria-label="Toggle sidebar">
        <Menu size={20} strokeWidth={1.8} />
      </button>
      <div className="top-bar__title-group">
        <span className="top-bar__conv-title">{title || "New Chat"}</span>
        <ChevronDown size={14} strokeWidth={1.8} className="top-bar__chevron" />
      </div>
      <div className="top-bar__tabs">
        <button className="top-bar__tab top-bar__tab--active">Chat</button>
        <button className="top-bar__tab">Code</button>
      </div>
      <button className="top-bar__action" aria-label="Share conversation">
        <Share2 size={15} strokeWidth={1.8} />
      </button>
    </div>
  );
}

function MessageList({
  messages,
  loading,
}: {
  messages: Message[];
  loading: boolean;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  function handleScroll() {
    const el = listRef.current;
    if (!el) return;
    isAtBottomRef.current =
      el.scrollTop + el.clientHeight >= el.scrollHeight - 50;
  }

  useEffect(() => {
    const el = listRef.current;
    if (el && isAtBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="message-list" ref={listRef} onScroll={handleScroll}>
      <div className="message-list__inner">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {loading && (
          <div className="msg-assistant-wrap">
            <div className="msg-assistant-logo">
              <ClaudeLogo size={20} />
            </div>
            <div className="thinking-indicator">Thinking…</div>
          </div>
        )}
      </div>
    </div>
  );
}

function InputArea({
  onSend,
  loading,
  model,
  onModelChange,
}: {
  onSend: (text: string) => void;
  loading: boolean;
  model: string;
  onModelChange: (m: string) => void;
}) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function adjustHeight() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }

  function submit() {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  const displayModel = model.split("/").pop() ?? model;

  return (
    <div className="input-area-wrap">
      <div className="input-card">
        <textarea
          ref={textareaRef}
          className="input-card__textarea"
          value={input}
          onChange={(e) => { setInput(e.target.value); adjustHeight(); }}
          onKeyDown={handleKeyDown}
          placeholder="Reply..."
          disabled={loading}
          rows={1}
          aria-label="Message input"
        />
        <div className="input-card__toolbar">
          <button className="input-card__icon-btn" title="Attach" aria-label="Attach file or image">
            <Plus size={16} strokeWidth={2} />
          </button>
          <div className="input-card__toolbar-right">
            <select
              className="input-card__model-select"
              aria-label="Select AI model"
              value={model}
              onChange={(e) => {
                const newModel = e.target.value;
                const configKey = MODEL_CONFIG_KEYS[newModel];
                const isConfigured = localStorage.getItem(configKey);

                // Always change the model
                onModelChange(newModel);

                // If not configured, show config dialog
                if (!isConfigured) {
                  setSelectedModel(newModel);
                  setConfigValue("");
                  setShowModelConfig(true);
                }
              }}
            >
              {MODELS.map((m) => (
                <option key={m} value={m}>{m.split("/").pop()}</option>
              ))}
            </select>
            {input.trim() ? (
              <button
                className="input-card__send-btn"
                title="Send"
                aria-label="Send message"
                onClick={submit}
                disabled={loading}
              >
                <ArrowUp size={16} strokeWidth={2.5} />
              </button>
            ) : (
              <button
                className="input-card__icon-btn"
                title="Voice input"
                aria-label="Send voice message"
              >
                <Mic size={16} strokeWidth={1.8} />
              </button>
            )}
          </div>
        </div>
      </div>
      <p className="input-disclaimer">
        ProteinClaw can make mistakes. Please double-check responses.
      </p>
    </div>
  );
}
