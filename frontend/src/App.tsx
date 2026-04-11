import { useCallback, useState, useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatWindow } from "./components/ChatWindow";
import { ApiKeysPanel } from "./components/ApiKeysPanel";
import { useChat } from "./hooks/useChat";
import { useProjects } from "./hooks/useProjects";
import { useStoredModel } from "./hooks/useStoredModel";
import type { Message } from "./types";

export default function App() {
  const [model, setModel] = useStoredModel();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark' | 'system'>(() => {
    const saved = localStorage.getItem('theme-preference');
    return (saved as 'light' | 'dark' | 'system') || 'system';
  });
  const [pendingProjectId, setPendingProjectId] = useState<string | null>(null);
  const [showApiKeys, setShowApiKeys] = useState(false);

  // Debug: log the backend port on mount
  useEffect(() => {
    const port = (window as any).__BACKEND_PORT__;
    const debugMode = (window as any).__DEBUG_MODE__;
    console.log('[ProteinClaw] Backend port:', port || 'NOT SET, using default 8000');
    console.log('[ProteinClaw] Debug mode:', debugMode);

    // Handle Cmd+Shift+I to log backend logs
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.code === 'KeyI') {
        e.preventDefault();
        console.log('[ProteinClaw] Cmd+Shift+I pressed - Check backend.log at ~/Library/Application Support/com.proteinclaw.app/backend.log');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Apply theme to document
  useEffect(() => {
    const applyTheme = (t: 'light' | 'dark' | 'system') => {
      const html = document.documentElement;
      if (t === 'system') {
        html.style.colorScheme = 'light dark';
        html.removeAttribute('data-theme');
      } else {
        html.style.colorScheme = t;
        html.setAttribute('data-theme', t);
      }
    };

    applyTheme(theme);
    localStorage.setItem('theme-preference', theme);
  }, [theme]);

  // Close sidebar on larger screens
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 768) {
        setSidebarOpen(false);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const {
    projects,
    activeConversationId,
    activeConversation,
    createProject,
    createConversation,
    selectConversation,
    appendMessage,
  } = useProjects();

  function handleNewChat() {
    let projectId: string;
    if (projects.length === 0) {
      projectId = createProject("My Chats");
    } else {
      projectId = projects[0].id;
    }
    // Set pending project but don't create conversation yet
    setPendingProjectId(projectId);
    selectConversation(projectId, 'pending');
  }

  const handleMessage = useCallback(
    (msg: Message) => {
      if (activeConversationId) {
        appendMessage(activeConversationId, msg);
      }
    },
    [activeConversationId, appendMessage]
  );

  const { loading, send, streamingAssistant } = useChat(
    activeConversationId ?? "",
    handleMessage
  );

  const displayMessages: Message[] = [
    ...(activeConversation?.messages ?? []),
    ...(streamingAssistant ? [streamingAssistant] : []),
  ];

  return (
    <div className="app-layout">
      <Sidebar
        projects={projects}
        activeConversationId={activeConversationId}
        onSelectConversation={(projectId, convId) => {
          selectConversation(projectId, convId);
          setSidebarOpen(false); // Close sidebar after selecting
        }}
        onNewChat={() => {
          handleNewChat();
          setSidebarOpen(false);
        }}
        isOpen={sidebarOpen}
        theme={theme}
        onThemeChange={setTheme}
        onOpenApiKeys={() => setShowApiKeys(true)}
      />
      {showApiKeys && (
        <ApiKeysPanel onClose={() => setShowApiKeys(false)} />
      )}
      <ChatWindow
        key={activeConversationId ?? "empty"}
        messages={displayMessages}
        loading={loading}
        title={activeConversation?.title ?? ""}
        model={model}
        onModelChange={setModel}
        hasConversation={activeConversationId !== null || pendingProjectId !== null}
        onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
        isPinned={activeConversation?.pinned ?? false}
        onPin={() => {
          if (activeConversationId) {
            // @ts-ignore - intentionally unused, TODO: implement state update
            const updatedProjects = projects.map(p => ({
              ...p,
              conversations: p.conversations.map(c =>
                c.id === activeConversationId ? { ...c, pinned: !c.pinned } : c
              ),
            }));
            // Update state (in a real app, you'd use a proper state management library)
            // For now, this would need to be handled through the useProjects hook
          }
        }}
        onRename={(newTitle) => {
          if (activeConversationId) {
            // @ts-ignore - intentionally unused, TODO: implement state update
            const updatedProjects = projects.map(p => ({
              ...p,
              conversations: p.conversations.map(c =>
                c.id === activeConversationId ? { ...c, title: newTitle } : c
              ),
            }));
            // Update state
          }
        }}
        onDelete={() => {
          if (activeConversationId) {
            // @ts-ignore - intentionally unused, TODO: implement state update
            const updatedProjects = projects.map(p => ({
              ...p,
              conversations: p.conversations.filter(c => c.id !== activeConversationId),
            }));
            selectConversation('', '');
            // Update state
          }
        }}
        onSend={(text) => {
          // If this is a pending conversation, create it now
          if (pendingProjectId && activeConversationId === 'pending') {
            const convId = createConversation(pendingProjectId, model);
            selectConversation(pendingProjectId, convId);
            // Use empty history for new conversation
            send(text, model, []);
            setPendingProjectId(null);
          } else {
            const history = (activeConversation?.messages ?? []).map((m) => ({
              role: m.role,
              content: m.content,
            }));
            send(text, model, history);
          }
        }}
      />
    </div>
  );
}
