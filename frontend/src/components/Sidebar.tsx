import {
  Plus,
  Search,
  Settings2,
  MessageSquare,
  FolderOpen,
  Box,
  ChevronDown,
} from "lucide-react";
import type { Project } from "../types";

interface Props {
  projects: Project[];
  activeConversationId: string | null;
  onSelectConversation: (projectId: string, conversationId: string) => void;
  onNewChat: () => void;
}

export function Sidebar({
  projects,
  activeConversationId,
  onSelectConversation,
  onNewChat,
}: Props) {
  const recents = projects
    .flatMap((p) => p.conversations.map((c) => ({ ...c, projectId: p.id })))
    .sort((a, b) => b.createdAt - a.createdAt)
    .slice(0, 30);

  return (
    <aside className="sidebar">
      {/* Top nav */}
      <div className="sidebar-nav">
        <button className="sidebar-nav-item sidebar-nav-item--primary" onClick={onNewChat}>
          <Plus size={16} strokeWidth={2} />
          <span>New chat</span>
        </button>
        <button className="sidebar-nav-item">
          <Search size={15} strokeWidth={1.8} />
          <span>Search</span>
        </button>
        <button className="sidebar-nav-item">
          <Settings2 size={15} strokeWidth={1.8} />
          <span>Customize</span>
        </button>
      </div>

      {/* Section links */}
      <div className="sidebar-sections">
        <button className="sidebar-section-item">
          <MessageSquare size={15} strokeWidth={1.8} />
          <span>Chats</span>
        </button>
        <button className="sidebar-section-item">
          <FolderOpen size={15} strokeWidth={1.8} />
          <span>Projects</span>
        </button>
        <button className="sidebar-section-item">
          <Box size={15} strokeWidth={1.8} />
          <span>Artifacts</span>
        </button>
      </div>

      {/* Recents */}
      <div className="sidebar-recents">
        <div className="sidebar-recents-label">Recents</div>
        <div className="sidebar-recents-list">
          {recents.length === 0 && (
            <div className="sidebar-empty">No conversations yet</div>
          )}
          {recents.map((item) => (
            <button
              key={item.id}
              className={`sidebar-conv-item${item.id === activeConversationId ? " active" : ""}`}
              onClick={() => onSelectConversation(item.projectId, item.id)}
              title={item.title}
            >
              <span className="sidebar-conv-title">{item.title}</span>
              {item.id === activeConversationId && (
                <span className="sidebar-conv-more">···</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* User profile */}
      <div className="sidebar-user">
        <div className="sidebar-user-avatar">P</div>
        <div className="sidebar-user-info">
          <span className="sidebar-user-name">ProteinClaw</span>
          <span className="sidebar-user-plan">Pro plan</span>
        </div>
        <ChevronDown size={14} strokeWidth={1.8} className="sidebar-user-chevron" />
      </div>
    </aside>
  );
}
