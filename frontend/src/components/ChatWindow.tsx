import { useState, useRef, useEffect } from "react";
import { Plus, Mic, Share2, ChevronDown, ArrowUp, Menu, FolderOpen, Monitor, PanelRight, X } from "lucide-react";
import type { Message } from "../types";
import { MessageBubble } from "./MessageBubble";
import { ClaudeLogo } from "./ClaudeLogo";
import { isTauri } from "../lib/storage";
import { invoke } from "@tauri-apps/api/core";

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
  onOpenApiKeys?: () => void;
  folderPath?: string | null;
  onSelectFolder?: (path: string) => void;
  prefillPrompt?: string;
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
  onOpenApiKeys,
  folderPath,
  onSelectFolder,
  prefillPrompt,
}: Props) {
  // @ts-ignore - intentionally declared, used in model config dialog
  const [showModelConfig, setShowModelConfig] = useState(false);
  // @ts-ignore - intentionally declared, used in model config dialog
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  // @ts-ignore - intentionally declared, used in model config dialog
  const [configValue, setConfigValue] = useState("");
  const [showRightSidebar, setShowRightSidebar] = useState(false);

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
    <div className="chat-window">
      <div className="chat-main">
      <TopBar title={title} onMenuToggle={onMenuToggle} onRightSidebarToggle={() => setShowRightSidebar(v => !v)} rightSidebarOpen={showRightSidebar} />
      <MessageList messages={messages} loading={loading} />
      <InputArea
        onSend={onSend}
        loading={loading}
        model={model}
        onModelChange={onModelChange}
        onOpenApiKeys={onOpenApiKeys}
        setShowModelConfig={setShowModelConfig}
        setSelectedModel={setSelectedModel}
        setConfigValue={setConfigValue}
        folderPath={folderPath}
        onSelectFolder={onSelectFolder}
        prefillPrompt={prefillPrompt}
      />

      </div>{/* end chat-main */}

      {/* Right Sidebar */}
      <div className={`right-sidebar${showRightSidebar ? " right-sidebar--open" : ""}`}>
        <div className="right-sidebar__header">
          <span className="right-sidebar__title">Details</span>
          <button
            className="right-sidebar__close"
            onClick={() => setShowRightSidebar(false)}
            aria-label="Close sidebar"
          >
            <X size={16} strokeWidth={1.8} />
          </button>
        </div>
        <div className="right-sidebar__body">
          <p className="right-sidebar__empty">No details available.</p>
        </div>
      </div>

      {/* Model Config Dialog */}
      {showModelConfig && (
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
              {selectedModel ? `Configure ${selectedModel.split("/").pop()}` : "Add a Model"}
            </h3>
            <p style={{ margin: '0 0 12px 0', fontSize: '14px', color: 'var(--text)', lineHeight: '1.5' }}>
              {selectedModel ? "Please provide the required configuration:" : "Select a model to configure:"}
            </p>

            {!selectedModel ? (
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) {
                    setSelectedModel(e.target.value);
                    setConfigValue("");
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
              >
                <option value="">Choose a model...</option>
                {MODELS.map((m) => {
                  const configKey = MODEL_CONFIG_KEYS[m];
                  const isConfigured = localStorage.getItem(configKey);
                  return !isConfigured ? (
                    <option key={m} value={m}>{m.split("/").pop()}</option>
                  ) : null;
                })}
              </select>
            ) : (
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
                    setSelectedModel(null);
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
            )}
            {selectedModel && (
              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => {
                    setShowModelConfig(false);
                    setSelectedModel(null);
                  }}
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
                      setSelectedModel(null);
                      setConfigValue("");
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
            )}
          </div>
        </>
      )}
    </div>
  );
}

function TopBar({
  title,
  onMenuToggle,
  onRightSidebarToggle,
  rightSidebarOpen,
}: {
  title: string;
  onMenuToggle?: () => void;
  onRightSidebarToggle?: () => void;
  rightSidebarOpen?: boolean;
}) {
  return (
    <div className="top-bar">
      <button className="mobile-menu-btn" onClick={onMenuToggle} aria-label="Toggle sidebar">
        <Menu size={20} strokeWidth={1.8} />
      </button>
      <div className="top-bar__title-group">
        <span className="top-bar__conv-title">{title || "New Chat"}</span>
        <ChevronDown size={14} strokeWidth={1.8} className="top-bar__chevron" />
      </div>
      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "4px" }}>
        <button className="top-bar__action" aria-label="Share conversation">
          <Share2 size={15} strokeWidth={1.8} />
        </button>
        <button
          className={`top-bar__action${rightSidebarOpen ? " top-bar__action--active" : ""}`}
          aria-label="Toggle right sidebar"
          onClick={onRightSidebarToggle}
          title="Sidebar"
        >
          <PanelRight size={16} strokeWidth={1.8} />
        </button>
      </div>
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
        {loading && !(messages.at(-1)?.role === 'assistant' && messages.at(-1)?.content) && (
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
  onOpenApiKeys,
  setShowModelConfig: _setShowModelConfig,
  setSelectedModel: _setSelectedModel,
  setConfigValue: _setConfigValue,
  folderPath,
  onSelectFolder,
  prefillPrompt,
}: {
  onSend: (text: string) => void;
  loading: boolean;
  model: string;
  onModelChange: (m: string) => void;
  onOpenApiKeys?: () => void;
  setShowModelConfig: (show: boolean) => void;
  setSelectedModel: (model: string | null) => void;
  setConfigValue: (value: string) => void;
  folderPath?: string | null;
  onSelectFolder?: (path: string) => void;
  prefillPrompt?: string;
}) {
  const [input, setInput] = useState(prefillPrompt ?? "");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isComposingRef = useRef(false);
  const justFinishedComposingRef = useRef(false);

  const isModelValid = Boolean(
    model && MODEL_CONFIG_KEYS[model] && localStorage.getItem(MODEL_CONFIG_KEYS[model])
  );

  function adjustHeight() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }

  useEffect(() => {
    if (prefillPrompt) adjustHeight();
  }, []);

  function submit() {
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing && !isComposingRef.current && !justFinishedComposingRef.current) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="input-area-wrap">
      <div className="input-card">
        <textarea
          ref={textareaRef}
          className="input-card__textarea"
          value={input}
          onChange={(e) => { setInput(e.target.value); adjustHeight(); }}
          onCompositionStart={() => { isComposingRef.current = true; }}
          onCompositionEnd={() => {
            isComposingRef.current = false;
            justFinishedComposingRef.current = true;
            setTimeout(() => { justFinishedComposingRef.current = false; }, 0);
          }}
          onKeyDown={handleKeyDown}
          placeholder={isModelValid ? "Reply..." : "Select a model first..."}
          disabled={loading || !isModelValid}
          rows={1}
          aria-label="Message input"
        />
        <div className="input-card__toolbar">
          <button className="input-card__icon-btn" title="Attach" aria-label="Attach file or image">
            <Plus size={16} strokeWidth={2} />
          </button>
          <div className="input-card__toolbar-right">
            <select
              className={`input-card__model-select${!isModelValid ? " input-card__model-select--highlight" : ""}`}
              aria-label="Select AI model"
              value={model}
              onChange={(e) => {
                if (e.target.value === "configure-model") {
                  onOpenApiKeys?.();
                } else {
                  onModelChange(e.target.value);
                }
              }}
            >
              <option value="">Select a model...</option>
              {MODELS.map((m) => {
                const configKey = MODEL_CONFIG_KEYS[m];
                const isConfigured = localStorage.getItem(configKey);

                return isConfigured ? (
                  <option key={m} value={m}>{m.split("/").pop()}</option>
                ) : null;
              })}
              <option value="configure-model">Configure model...</option>
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
      <div className="input-subbar">
        <button
          className="input-subbar__btn"
          title={folderPath ?? "Select folder"}
          onClick={async () => {
            console.log('[folder] isTauri:', isTauri(), 'window.__TAURI__:', !!(window as any).__TAURI__);
            try {
              const selected = await invoke<string | null>("pick_folder");
              console.log('[folder] selected:', selected);
              if (selected) onSelectFolder?.(selected);
            } catch (e) {
              console.error('[folder] pick_folder error:', e);
            }
          }}
        >
          <FolderOpen size={13} strokeWidth={1.8} />
          <span>{folderPath ? folderPath.split("/").pop() : "Select folder"}</span>
        </button>
        <button className="input-subbar__btn" title="Environment">
          <Monitor size={13} strokeWidth={1.8} />
          <span>Local</span>
          <ChevronDown size={11} strokeWidth={2} />
        </button>
      </div>
      <p className="input-disclaimer">
        ProteinClaw can make mistakes. Please double-check responses.
      </p>
    </div>
  );
}
