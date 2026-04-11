import { useState } from "react";
import {
  Plus,
  Search,
  Puzzle,
  Settings,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  ListFilter,
  FolderPlus,
  FolderOpen,
  MoreVertical,
  Folder,
  Code,
  PencilLine,
  Archive,
  Trash2,
  Sun,
  Moon,
  Laptop,
  Palette,
} from "lucide-react";
import type { Project } from "../types";

function TriangleDown({ size = 8 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 12 12"
      fill="currentColor"
      style={{ display: "block" }}
    >
      <polygon points="1,3 11,3 6,10" />
    </svg>
  );
}

function TriangleRight({ size = 8 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 12 12"
      fill="currentColor"
      style={{ display: "block" }}
    >
      <polygon points="3,1 3,11 10,6" />
    </svg>
  );
}

interface Props {
  projects: Project[];
  activeConversationId: string | null;
  onSelectConversation: (projectId: string, conversationId: string) => void;
  onNewChat: () => void;
  isOpen?: boolean;
  onToggle?: () => void;
  theme?: 'light' | 'dark' | 'system';
  onThemeChange?: (theme: 'light' | 'dark' | 'system') => void;
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const minutes = Math.floor(diff / 60000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(diff / 3600000);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(diff / 86400000);
  if (days < 7) return `${days}d`;
  const weeks = Math.floor(days / 7);
  if (weeks < 5) return `${weeks}w`;
  const months = Math.floor(days / 30);
  return `${months}mo`;
}

const CONV_LIMIT = 5;

export function Sidebar({
  projects,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  isOpen = false,
  onToggle,
  theme = 'system',
  onThemeChange,
}: Props) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [allCollapsed, setAllCollapsed] = useState(false);
  const [showAllMap, setShowAllMap] = useState<Record<string, boolean>>({});
  const [hoveredProject, setHoveredProject] = useState<string | null>(null);
  const [lockedProject, setLockedProject] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showAppearance, setShowAppearance] = useState(false);

  function toggleProject(id: string) {
    setCollapsed((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  function toggleShowAll(projectId: string) {
    setShowAllMap((prev) => ({ ...prev, [projectId]: !prev[projectId] }));
  }

  function handleCollapseAll() {
    const next = !allCollapsed;
    setAllCollapsed(next);
    const map: Record<string, boolean> = {};
    projects.forEach((p) => { map[p.id] = next; });
    setCollapsed(map);
  }

  const activeProjects = projects.filter((p) => p.conversations.length > 0);

  return (
    <aside className={`sidebar${isOpen ? " open" : ""}`}>
      {/* Top nav */}
      <div className="sidebar-nav">
        <button
          className="sidebar-nav-item sidebar-nav-item--primary"
          onClick={onNewChat}
        >
          <Plus size={16} strokeWidth={2} />
          <span>New chat</span>
        </button>
        <button className="sidebar-nav-item" aria-label="Search conversations">
          <Search size={15} strokeWidth={1.8} />
          <span>Search</span>
        </button>
        <button className="sidebar-nav-item" aria-label="View plugins">
          <Puzzle size={15} strokeWidth={1.8} />
          <span>Plugins</span>
        </button>
      </div>

      {/* Threads */}
      <div className="sidebar-threads">
        <div className="sidebar-threads-header">
          <span className="sidebar-threads-label">Sessions</span>
          <div className="sidebar-threads-actions">
            <button
              className="sidebar-threads-btn"
              title={allCollapsed ? "Expand all" : "Collapse all"}
              aria-label={allCollapsed ? "Expand all sessions" : "Collapse all sessions"}
              onClick={handleCollapseAll}
            >
              <ChevronsUpDown size={13} strokeWidth={1.8} />
            </button>
            <button className="sidebar-threads-btn" title="Filter" aria-label="Filter sessions">
              <ListFilter size={13} strokeWidth={1.8} />
            </button>
            <button className="sidebar-threads-btn" title="New project" aria-label="Create new project">
              <FolderPlus size={13} strokeWidth={1.8} />
            </button>
          </div>
        </div>
        <div className="sidebar-threads-list">
          {activeProjects.length === 0 && (
            <div className="sidebar-empty">No conversations yet</div>
          )}
          {activeProjects.map((project) => {
            const isCollapsed = collapsed[project.id];
            const showAll = showAllMap[project.id];
            const convs = [...project.conversations].sort(
              (a, b) => b.createdAt - a.createdAt
            );
            const visible = showAll ? convs : convs.slice(0, CONV_LIMIT);
            const hasMore = convs.length > CONV_LIMIT;

            return (
              <div key={project.id} className="sidebar-project-group">
                <div
                  className="sidebar-project-header-wrapper"
                  onMouseEnter={() => setHoveredProject(project.id)}
                  onMouseLeave={() => setHoveredProject(null)}
                >
                  <button
                    className="sidebar-project-header"
                    onClick={() => toggleProject(project.id)}
                  >
                    <div className="sidebar-project-icon-container">
                      <FolderOpen size={15} strokeWidth={1.9} className="sidebar-project-icon" />
                      <div className="sidebar-project-chevron">
                        {isCollapsed ? (
                          <TriangleRight size={8} />
                        ) : (
                          <TriangleDown size={8} />
                        )}
                      </div>
                    </div>
                    <span className="sidebar-project-name">{project.name}</span>
                  </button>
                  {(hoveredProject === project.id || lockedProject === project.id) && (
                    <div className="sidebar-project-actions">
                      <button
                        className="sidebar-project-action-btn"
                        title="New chat"
                        aria-label={`Create new chat in ${project.name}`}
                        onClick={() => onNewChat()}
                      >
                        <PencilLine size={14} strokeWidth={1.8} />
                      </button>
                      <div className="sidebar-project-menu-container">
                        <button
                          className="sidebar-project-action-btn"
                          title="More options"
                          aria-label={`Options for ${project.name}`}
                          aria-expanded={lockedProject === project.id}
                          onClick={() => {
                            if (lockedProject === project.id) {
                              setLockedProject(null);
                            } else {
                              setLockedProject(project.id);
                            }
                          }}
                        >
                          <MoreVertical size={14} strokeWidth={2} />
                        </button>
                        {lockedProject === project.id && (
                        <div className="sidebar-project-menu">
                          <button className="sidebar-menu-item">
                            <Folder size={13} strokeWidth={1.8} />
                            <span>Open in Finder</span>
                          </button>
                          <button className="sidebar-menu-item">
                            <PencilLine size={13} strokeWidth={1.8} />
                            <span>Edit name</span>
                          </button>
                          <button className="sidebar-menu-item sidebar-menu-item--danger">
                            <Trash2 size={13} strokeWidth={1.8} />
                            <span>Remove</span>
                          </button>
                        </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {!isCollapsed && (
                  <div className="sidebar-project-convs">
                    {visible.map((conv) => (
                      <button
                        key={conv.id}
                        className={`sidebar-conv-item${conv.id === activeConversationId ? " active" : ""}`}
                        onClick={() => onSelectConversation(project.id, conv.id)}
                        title={conv.title}
                      >
                        <span className="sidebar-conv-title">{conv.title}</span>
                        <span className="sidebar-conv-time">
                          {relativeTime(conv.createdAt)}
                        </span>
                      </button>
                    ))}
                    {hasMore && (
                      <button
                        className="sidebar-show-more"
                        onClick={() => toggleShowAll(project.id)}
                      >
                        {showAll ? "Show less" : "Show more"}
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        <div style={{ position: 'relative' }}>
          <button
            className="sidebar-nav-item"
            aria-label="Open settings"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings size={15} strokeWidth={1.8} />
            <span>Settings</span>
          </button>
          {showSettings && (
            <div className="sidebar-project-menu" style={{ bottom: '100%', top: 'auto', marginBottom: '4px' }}>
              <button
                className="sidebar-menu-item"
                onClick={() => setShowAppearance(!showAppearance)}
              >
                <Palette size={13} strokeWidth={1.8} />
                <span>Appearance</span>
                <span style={{ marginLeft: 'auto' }}>
                  {showAppearance ? (
                    <ChevronDown size={13} strokeWidth={1.8} />
                  ) : (
                    <ChevronRight size={13} strokeWidth={1.8} />
                  )}
                </span>
              </button>
              {showAppearance && (
                <>
                  <button
                    className="sidebar-menu-item"
                    onClick={() => {
                      onThemeChange?.('light');
                      setShowSettings(false);
                      setShowAppearance(false);
                    }}
                    style={{ paddingLeft: '28px' }}
                  >
                    <Sun size={13} strokeWidth={1.8} />
                    <span>Light</span>
                    {theme === 'light' && <span style={{ marginLeft: 'auto' }}>✓</span>}
                  </button>
                  <button
                    className="sidebar-menu-item"
                    onClick={() => {
                      onThemeChange?.('dark');
                      setShowSettings(false);
                      setShowAppearance(false);
                    }}
                    style={{ paddingLeft: '28px' }}
                  >
                    <Moon size={13} strokeWidth={1.8} />
                    <span>Dark</span>
                    {theme === 'dark' && <span style={{ marginLeft: 'auto' }}>✓</span>}
                  </button>
                  <button
                    className="sidebar-menu-item"
                    onClick={() => {
                      onThemeChange?.('system');
                      setShowSettings(false);
                      setShowAppearance(false);
                    }}
                    style={{ paddingLeft: '28px' }}
                  >
                    <Laptop size={13} strokeWidth={1.8} />
                    <span>System</span>
                    {theme === 'system' && <span style={{ marginLeft: 'auto' }}>✓</span>}
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
