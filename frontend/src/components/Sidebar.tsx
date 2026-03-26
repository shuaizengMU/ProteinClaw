import { useState, useEffect, useRef } from "react";
import type { Project } from "../types";
import { ProjectItem } from "./ProjectItem";

interface Props {
  projects: Project[];
  activeConversationId: string | null;
  expandedProjectId: string | null;
  model: string;
  onSelectConversation: (projectId: string, conversationId: string) => void;
  onCreateProject: (name: string) => string;
  onCreateConversation: (projectId: string, model: string) => string;
  onToggleProject: (projectId: string) => void;
}

export function Sidebar({
  projects,
  activeConversationId,
  expandedProjectId,
  model,
  onSelectConversation,
  onCreateProject,
  onCreateConversation,
  onToggleProject,
}: Props) {
  const [newProjectMode, setNewProjectMode] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (newProjectMode) inputRef.current?.focus();
  }, [newProjectMode]);

  function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    const name = newProjectName.trim();
    if (!name) return;
    onCreateProject(name);
    setNewProjectName("");
    setNewProjectMode(false);
  }

  function handleInputBlur() {
    setNewProjectMode(false);
    setNewProjectName("");
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        {newProjectMode ? (
          <form onSubmit={handleCreateProject} className="inline-input-form">
            <input
              ref={inputRef}
              className="inline-input"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              onBlur={handleInputBlur}
              placeholder="Project name"
            />
          </form>
        ) : (
          <button
            className="new-project-btn"
            onClick={() => setNewProjectMode(true)}
          >
            + New Project
          </button>
        )}
      </div>

      <div className="project-list">
        {projects.map((project) => (
          <ProjectItem
            key={project.id}
            project={project}
            isExpanded={expandedProjectId === project.id}
            activeConversationId={activeConversationId}
            onToggle={() => onToggleProject(project.id)}
            onSelectConversation={(convId) =>
              onSelectConversation(project.id, convId)
            }
            onNewChat={() => {
              const id = onCreateConversation(project.id, model);
              onSelectConversation(project.id, id);
            }}
          />
        ))}
      </div>
    </aside>
  );
}
