import { useCallback, useState, useEffect, useRef } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatWindow } from "./components/ChatWindow";
import { CaseStudyPage } from "./components/CaseStudyPage";
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
  const [appLoading, setAppLoading] = useState(false);
  const newConvIdRef = useRef<string | null>(null);
  const [currentView, setCurrentView] = useState<'chat' | 'case-study'>('chat');
  const pendingPromptRef = useRef<string | null>(null);

  const handleCloseApiKeys = useCallback(() => setShowApiKeys(false), []);

  // Debug: log the backend port on mount
  useEffect(() => {
    if (import.meta.env.DEV) {
      const port = (window as any).__BACKEND_PORT__;
      console.log('[ProteinClaw] Backend port:', port || 'NOT SET, using default 8000');
    }

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
    loaded,
    activeProjectId,
    activeConversationId,
    activeConversation,
    createProject,
    createConversation,
    selectConversation,
    appendMessage,
    updateConversationTitle,
    deleteConversation,
    togglePinConversation,
    updateProjectFolder,
  } = useProjects();

  const activeProject = projects.find((p) => p.id === activeProjectId) ?? null;

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

  function handleTryIt(prompt: string) {
    pendingPromptRef.current = prompt;
    handleNewChat();
    setCurrentView('chat');
  }

  const handleMessage = useCallback(
    (msg: Message) => {
      if (msg.role === 'assistant') setAppLoading(false);
      // Use the ref if it's set (for newly created conversations during pending flow)
      // Otherwise use the state value
      const convId = newConvIdRef.current || activeConversationId;
      if (convId) {
        appendMessage(convId, msg);
      }
    },
    [activeConversationId, appendMessage]
  );

  const { loading, send, streamingAssistant } = useChat(
    activeConversationId ?? "",
    handleMessage
  );

  if (!loaded) return null;

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
          setSidebarOpen(false);
          setCurrentView('chat');
          pendingPromptRef.current = null;
        }}
        onNewChat={() => {
          handleNewChat();
          setSidebarOpen(false);
          setCurrentView('chat');
        }}
        onDeleteConversation={(convId) => {
          deleteConversation(convId);
          if (activeConversationId === convId) selectConversation('', '');
        }}
        onRenameConversation={updateConversationTitle}
        onPinConversation={togglePinConversation}
        isOpen={sidebarOpen}
        theme={theme}
        onThemeChange={setTheme}
        onOpenApiKeys={() => setShowApiKeys(true)}
        onNavigate={(view) => setCurrentView(view)}
      />
      {showApiKeys && (
        <ApiKeysPanel onClose={handleCloseApiKeys} />
      )}
      {currentView === 'case-study' ? (
        <CaseStudyPage onTryIt={handleTryIt} />
      ) : (
        <ChatWindow
          key={activeConversationId ?? "empty"}
          messages={displayMessages}
          loading={loading || appLoading}
          title={activeConversation?.title ?? ""}
          model={model}
          onModelChange={setModel}
          onOpenApiKeys={() => setShowApiKeys(true)}
          hasConversation={activeConversationId !== null || pendingProjectId !== null}
          onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
          folderPath={activeProject?.folderPath ?? null}
          onSelectFolder={(path) => {
            if (activeProjectId) updateProjectFolder(activeProjectId, path);
          }}
          prefillPrompt={pendingPromptRef.current ?? undefined}
          onSend={(text) => {
            pendingPromptRef.current = null;
            setAppLoading(true);
            // If this is a pending conversation, create it now
            if (pendingProjectId && activeConversationId === 'pending') {
              const convId = createConversation(pendingProjectId, model);
              newConvIdRef.current = convId;
              // Auto-title from first message (explicit, before re-render)
              updateConversationTitle(convId, text.slice(0, 60));
              selectConversation(pendingProjectId, convId);
              // Use empty history for new conversation
              send(text, model, []);
              newConvIdRef.current = null;
              setPendingProjectId(null);
            } else {
              // Auto-title if this is the first message in an existing "New Chat"
              if (activeConversationId && activeConversation?.title === "New Chat" && activeConversation.messages.length === 0) {
                updateConversationTitle(activeConversationId, text.slice(0, 60));
              }
              const history = (activeConversation?.messages ?? []).map((m) => ({
                role: m.role,
                content: m.content,
              }));
              send(text, model, history);
            }
          }}
        />
      )}
    </div>
  );
}
