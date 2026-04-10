import { useCallback } from "react";
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
        onSelectConversation={selectConversation}
        onNewChat={handleNewChat}
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
