import { useState, useCallback } from "react";
import type { Project, Conversation, Message } from "../types";
import { loadProjects, saveProjects } from "../lib/storage";

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>(() => loadProjects());
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  function createProject(name: string): string {
    const id = crypto.randomUUID();
    const project: Project = { id, name, createdAt: Date.now(), conversations: [] };
    setProjects((prev) => {
      const updated = [project, ...prev];
      saveProjects(updated);
      return updated;
    });
    return id;
  }

  function createConversation(projectId: string, model: string): string {
    const id = crypto.randomUUID();
    const conversation: Conversation = {
      id,
      title: "New Chat",
      model,
      createdAt: Date.now(),
      messages: [],
    };
    setProjects((prev) => {
      const updated = prev.map((p) =>
        p.id === projectId
          ? { ...p, conversations: [conversation, ...p.conversations] }
          : p
      );
      saveProjects(updated);
      return updated;
    });
    return id;
  }

  function selectConversation(projectId: string, conversationId: string): void {
    setActiveProjectId(projectId);
    setActiveConversationId(conversationId);
  }

  const appendMessage = useCallback(
    (conversationId: string, message: Message): void => {
      setProjects((prev) => {
        const updated = prev.map((p) => ({
          ...p,
          conversations: p.conversations.map((c) => {
            if (c.id !== conversationId) return c;
            const messages = [...c.messages, message];
            // Auto-set title from first user message
            const title =
              c.title === "New Chat" && message.role === "user"
                ? message.content.slice(0, 60)
                : c.title;
            return { ...c, messages, title };
          }),
        }));
        saveProjects(updated);
        return updated;
      });
    },
    [] // only uses setProjects (stable) and saveProjects (module-level)
  );

  const activeConversation =
    projects
      .find((p) => p.id === activeProjectId)
      ?.conversations.find((c) => c.id === activeConversationId) ?? null;

  return {
    projects,
    activeProjectId,
    activeConversationId,
    activeConversation,
    createProject,
    createConversation,
    selectConversation,
    appendMessage,
  };
}
