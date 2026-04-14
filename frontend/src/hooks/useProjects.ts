import { useState, useCallback, useEffect } from "react";
import type { Project, ConversationMeta, Conversation, Message } from "../types";
import {
  loadIndex,
  saveIndex,
  loadConversationMessages,
  saveConversationMessages,
  deleteConversationFile,
} from "../lib/storage";

export function useProjects() {
  // Metadata only — fast to load, always in memory
  const [projects, setProjects] = useState<Project[]>([]);
  const [loaded, setLoaded] = useState(false);

  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  // Messages for the currently open conversation
  const [activeMessages, setActiveMessages] = useState<Message[]>([]);

  // Load index on mount
  useEffect(() => {
    loadIndex().then((data) => {
      setProjects(data);
      setLoaded(true);
    });
  }, []);

  // Load messages when active conversation changes
  useEffect(() => {
    if (!activeConversationId || activeConversationId === "pending") {
      setActiveMessages([]);
      return;
    }
    loadConversationMessages(activeConversationId).then(setActiveMessages);
  }, [activeConversationId]);

  // ── Metadata helpers ────────────────────────────────────────────────────

  function updateIndex(updater: (prev: Project[]) => Project[]) {
    setProjects((prev) => {
      const next = updater(prev);
      saveIndex(next);
      return next;
    });
  }

  // ── Project operations ───────────────────────────────────────────────────

  function createProject(name: string): string {
    const id = crypto.randomUUID();
    updateIndex((prev) => [{ id, name, createdAt: Date.now(), conversations: [] }, ...prev]);
    return id;
  }

  // ── Conversation operations ──────────────────────────────────────────────

  function createConversation(projectId: string, model: string): string {
    const id = crypto.randomUUID();
    const meta: ConversationMeta = { id, title: "New Chat", model, createdAt: Date.now() };
    // Create empty messages file immediately
    saveConversationMessages(id, []);
    updateIndex((prev) =>
      prev.map((p) =>
        p.id === projectId
          ? { ...p, conversations: [meta, ...p.conversations] }
          : p
      )
    );
    return id;
  }

  function selectConversation(projectId: string, conversationId: string): void {
    setActiveProjectId(projectId);
    setActiveConversationId(conversationId);
  }

  const appendMessage = useCallback(
    (conversationId: string, message: Message): void => {
      setActiveMessages((prev) => {
        const next = [...prev, message];
        saveConversationMessages(conversationId, next);
        return next;
      });
    },
    []
  );

  const updateConversationTitle = useCallback(
    (conversationId: string, title: string): void => {
      updateIndex((prev) =>
        prev.map((p) => ({
          ...p,
          conversations: p.conversations.map((c) =>
            c.id === conversationId ? { ...c, title } : c
          ),
        }))
      );
    },
    []
  );

  const deleteConversation = useCallback((conversationId: string): void => {
    deleteConversationFile(conversationId);
    updateIndex((prev) =>
      prev.map((p) => ({
        ...p,
        conversations: p.conversations.filter((c) => c.id !== conversationId),
      }))
    );
  }, []);

  const togglePinConversation = useCallback((conversationId: string): void => {
    updateIndex((prev) =>
      prev.map((p) => ({
        ...p,
        conversations: p.conversations.map((c) =>
          c.id === conversationId ? { ...c, pinned: !c.pinned } : c
        ),
      }))
    );
  }, []);

  const updateProjectFolder = useCallback((projectId: string, folderPath: string): void => {
    updateIndex((prev) =>
      prev.map((p) => (p.id === projectId ? { ...p, folderPath } : p))
    );
  }, []);

  // ── Derived values ───────────────────────────────────────────────────────

  const activeConversationMeta =
    projects
      .find((p) => p.id === activeProjectId)
      ?.conversations.find((c) => c.id === activeConversationId) ?? null;

  // Combine metadata + loaded messages into a single object for App.tsx
  const activeConversation: Conversation | null = activeConversationMeta
    ? { ...activeConversationMeta, messages: activeMessages }
    : null;

  return {
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
  };
}
