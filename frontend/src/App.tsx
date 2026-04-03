import { useState, useCallback } from "react";
import { Sidebar } from "./components/Sidebar";
import { ChatWindow } from "./components/ChatWindow";
import { useChat } from "./hooks/useChat";
import { useProjects } from "./hooks/useProjects";
import { useStoredModel } from "./hooks/useStoredModel";
import type { Message } from "./types";

export default function App() {
  const [model, setModel] = useStoredModel();

  const {
    projects,
    activeConversationId,
    activeConversation,
    createProject,
    createConversation,
    selectConversation,
    appendMessage,
  } = useProjects();

  // Track which project is expanded in the sidebar
  const [expandedProjectId, setExpandedProjectId] = useState<string | null>(
    null
  );

  function handleCreateProject(name: string): string {
    const id = createProject(name);
    setExpandedProjectId(id); // auto-expand new project
    return id;
  }

  function handleToggleProject(projectId: string) {
    setExpandedProjectId((prev) => (prev === projectId ? null : projectId));
  }

  // Persists each logical message to the active conversation.
  // Memoized so useChat's onMessageRef always holds the latest version
  // without triggering WS reconnects. Stale-conversation safety comes from
  // useChat closing the WS on conversationId change, not from this guard.
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

  // Merge persisted messages with the live streaming assistant message.
  // React 19 batches the appendMessage(assistantMsg) + setStreamingAssistant(null)
  // calls that fire together on WS done, so there is no duplicate or flash.
  const displayMessages: Message[] = [
    ...(activeConversation?.messages ?? []),
    ...(streamingAssistant ? [streamingAssistant] : []),
  ];

  return (
    <div className="app-layout">
      <Sidebar
        projects={projects}
        activeConversationId={activeConversationId}
        expandedProjectId={expandedProjectId}
        model={model}
        onSelectConversation={selectConversation}
        onCreateProject={handleCreateProject}
        onCreateConversation={createConversation}
        onToggleProject={handleToggleProject}
      />
      <ChatWindow
        key={activeConversationId ?? "empty"}
        messages={displayMessages}
        loading={loading}
        title={activeConversation?.title ?? ""}
        model={model}
        onModelChange={setModel}
        hasConversation={activeConversationId !== null}
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
