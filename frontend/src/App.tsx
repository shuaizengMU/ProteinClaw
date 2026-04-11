import { useCallback, useState, useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatWindow } from "./components/ChatWindow";
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
    const convId = createConversation(projectId, model);
    selectConversation(projectId, convId);
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
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        theme={theme}
        onThemeChange={setTheme}
      />
      <ChatWindow
        key={activeConversationId ?? "empty"}
        messages={displayMessages}
        loading={loading}
        title={activeConversation?.title ?? ""}
        model={model}
        onModelChange={setModel}
        hasConversation={activeConversationId !== null}
        onMenuToggle={() => setSidebarOpen(!sidebarOpen)}
        onSend={(text) => {
          const history = (activeConversation?.messages ?? []).map((m) => ({
            role: m.role,
            content: m.content,
          }));
          send(text, model, history);
        }}
      />
    </div>
  );
}
