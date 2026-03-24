import { ChatWindow } from "./components/ChatWindow";
import { ModelSelector, useStoredModel } from "./components/ModelSelector";
import { useChat } from "./hooks/useChat";

export default function App() {
  const [model, setModel] = useStoredModel();
  const { messages, loading, send } = useChat();

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", fontFamily: "sans-serif" }}>
      <header style={{ display: "flex", alignItems: "center", padding: "8px 16px", borderBottom: "1px solid #ddd" }}>
        <h2 style={{ margin: 0 }}>ProteinClaw</h2>
        <ModelSelector value={model} onChange={setModel} />
      </header>
      <main style={{ flex: 1, overflow: "hidden" }}>
        <ChatWindow messages={messages} loading={loading} onSend={(text) => send(text, model)} />
      </main>
    </div>
  );
}
