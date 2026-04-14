import { invoke } from "@tauri-apps/api/core";
import type { Project, ConversationMeta, Message } from "../types";

const LS_KEY = "proteinclaw_projects";

export function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI__" in window;
}

// ── Migration from old single-file format ─────────────────────────────────

interface LegacyConversation extends ConversationMeta {
  messages: Message[];
}

interface LegacyProject extends Omit<Project, "conversations"> {
  conversations: LegacyConversation[];
}

async function migrateFromLegacy(): Promise<Project[]> {
  try {
    const raw = await invoke<string>("load_projects");
    if (!raw || raw === "null") return [];

    const legacy = JSON.parse(raw) as LegacyProject[];

    // Write each conversation's messages to its own file
    for (const project of legacy) {
      for (const conv of project.conversations) {
        await saveConversationMessages(conv.id, conv.messages);
      }
    }

    // Build metadata-only projects
    const projects: Project[] = legacy.map((p) => ({
      id: p.id,
      name: p.name,
      createdAt: p.createdAt,
      folderPath: p.folderPath,
      conversations: p.conversations.map(({ id, title, model, createdAt, pinned }) => ({
        id, title, model, createdAt, pinned,
      })),
    }));

    await saveIndex(projects);
    await invoke("delete_legacy_projects");
    return projects;
  } catch (e) {
    console.error("[storage] migration failed:", e);
    return [];
  }
}

// ── Index (metadata) ──────────────────────────────────────────────────────

export async function loadIndex(): Promise<Project[]> {
  if (isTauri()) {
    try {
      const raw = await invoke<string>("load_index");
      if (raw && raw !== "null") {
        return JSON.parse(raw) as Project[];
      }
      // First launch: try migrating from old format
      return await migrateFromLegacy();
    } catch (e) {
      console.error("[storage] load_index failed:", e);
      return [];
    }
  }
  // Browser fallback (dev without Tauri)
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const legacy = JSON.parse(raw) as LegacyProject[];
    return legacy.map((p) => ({
      ...p,
      conversations: p.conversations.map(({ id, title, model, createdAt, pinned }) => ({
        id, title, model, createdAt, pinned,
      })),
    }));
  } catch {
    return [];
  }
}

export async function saveIndex(projects: Project[]): Promise<void> {
  if (isTauri()) {
    try {
      await invoke("save_index", { data: JSON.stringify(projects) });
      return;
    } catch (e) {
      console.error("[storage] save_index failed:", e);
    }
  }
  // Browser fallback: store metadata only
  localStorage.setItem(LS_KEY + "_meta", JSON.stringify(projects));
}

// ── Conversation messages ─────────────────────────────────────────────────

export async function loadConversationMessages(id: string): Promise<Message[]> {
  if (isTauri()) {
    try {
      const raw = await invoke<string>("load_conversation", { id });
      if (raw && raw !== "null") {
        return JSON.parse(raw) as Message[];
      }
      return [];
    } catch (e) {
      console.error(`[storage] load_conversation(${id}) failed:`, e);
      return [];
    }
  }
  // Browser fallback
  try {
    const raw = localStorage.getItem(`conv_${id}`);
    return raw ? (JSON.parse(raw) as Message[]) : [];
  } catch {
    return [];
  }
}

export async function saveConversationMessages(id: string, messages: Message[]): Promise<void> {
  if (isTauri()) {
    try {
      await invoke("save_conversation", { id, data: JSON.stringify(messages) });
      return;
    } catch (e) {
      console.error(`[storage] save_conversation(${id}) failed:`, e);
    }
  }
  localStorage.setItem(`conv_${id}`, JSON.stringify(messages));
}

export async function deleteConversationFile(id: string): Promise<void> {
  if (isTauri()) {
    try {
      await invoke("delete_conversation_file", { id });
    } catch (e) {
      console.error(`[storage] delete_conversation_file(${id}) failed:`, e);
    }
  } else {
    localStorage.removeItem(`conv_${id}`);
  }
}
