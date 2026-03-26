import type { Project } from "../types";

interface Props {
  project: Project;
  isExpanded: boolean;
  activeConversationId: string | null;
  onToggle: () => void;
  onSelectConversation: (conversationId: string) => void;
  onNewChat: () => void;
}

export function ProjectItem({
  project,
  isExpanded,
  activeConversationId,
  onToggle,
  onSelectConversation,
  onNewChat,
}: Props) {
  return (
    <div className="project-item">
      <button className="project-header" onClick={onToggle}>
        <span className="project-name">{project.name}</span>
        <span className="project-meta">{project.conversations.length}</span>
        <span className="project-toggle">{isExpanded ? "▾" : "▸"}</span>
      </button>

      {isExpanded && (
        <div className="conversation-list">
          <button className="new-chat-btn" onClick={onNewChat}>
            ＋ New Chat
          </button>
          {project.conversations.map((conv) => (
            <button
              key={conv.id}
              className={`conversation-item${conv.id === activeConversationId ? " active" : ""}`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <span className="conversation-title">
                {conv.title.length > 40
                  ? conv.title.slice(0, 40) + "…"
                  : conv.title}
              </span>
              <span className="conversation-date">
                {formatRelativeDate(conv.createdAt)}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function formatRelativeDate(ts: number): string {
  const diff = Date.now() - ts;
  const days = Math.floor(diff / 86_400_000);
  if (days === 0) return "today";
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  return new Date(ts).toLocaleDateString();
}
