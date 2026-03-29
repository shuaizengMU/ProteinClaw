use crossterm::event::KeyEvent;
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Events consumed by the App state machine.
pub enum AppEvent {
    Key(KeyEvent),
    Resize(u16, u16),
    WsMessage(AgentEvent),
    WsError(String),
    ServerReady(u16),   // port
    ServerFailed(String),
    Tick,
}

/// Events received from the Python agent via WebSocket.
#[derive(Debug)]
pub enum AgentEvent {
    Thinking(String),
    Token(String),
    ToolCall { tool: String, args: Value },
    Observation { result: Value },
    Done,
    Error(String),
}

/// Raw flat JSON structure sent by the server.
#[derive(Deserialize)]
struct RawEvent {
    #[serde(rename = "type")]
    event_type: String,
    content: Option<String>,
    tool: Option<String>,
    args: Option<Value>,
    result: Option<Value>,
    message: Option<String>,
}

impl AgentEvent {
    pub fn from_json(json: &str) -> anyhow::Result<Self> {
        let raw: RawEvent = serde_json::from_str(json)?;
        match raw.event_type.as_str() {
            "thinking" => Ok(AgentEvent::Thinking(raw.content.unwrap_or_default())),
            "token"    => Ok(AgentEvent::Token(raw.content.unwrap_or_default())),
            "tool_call" => Ok(AgentEvent::ToolCall {
                tool: raw.tool.unwrap_or_default(),
                args: raw.args.unwrap_or(Value::Null),
            }),
            "observation" => Ok(AgentEvent::Observation {
                result: raw.result.unwrap_or(Value::Null),
            }),
            "done"  => Ok(AgentEvent::Done),
            "error" => Ok(AgentEvent::Error(raw.message.unwrap_or_default())),
            t => anyhow::bail!("Unknown event type: {}", t),
        }
    }
}

/// Outgoing WebSocket message to the Python server.
#[derive(Serialize)]
pub struct WsQuery {
    pub message: String,
    pub history: Vec<HistoryEntry>,
    pub model: String,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct HistoryEntry {
    pub role: String,
    pub content: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_token_event() {
        let json = r#"{"type":"token","content":"Hello"}"#;
        let event = AgentEvent::from_json(json).unwrap();
        assert!(matches!(event, AgentEvent::Token(s) if s == "Hello"));
    }

    #[test]
    fn parse_tool_call_event() {
        let json = r#"{"type":"tool_call","tool":"uniprot","args":{"id":"P04637"}}"#;
        let event = AgentEvent::from_json(json).unwrap();
        assert!(matches!(event, AgentEvent::ToolCall { tool, .. } if tool == "uniprot"));
    }

    #[test]
    fn parse_observation_event() {
        let json = r#"{"type":"observation","tool":"uniprot","result":{"name":"TP53"}}"#;
        let event = AgentEvent::from_json(json).unwrap();
        assert!(matches!(event, AgentEvent::Observation { .. }));
    }

    #[test]
    fn parse_done_event() {
        let json = r#"{"type":"done"}"#;
        let event = AgentEvent::from_json(json).unwrap();
        assert!(matches!(event, AgentEvent::Done));
    }

    #[test]
    fn parse_error_event() {
        let json = r#"{"type":"error","message":"API key missing"}"#;
        let event = AgentEvent::from_json(json).unwrap();
        assert!(matches!(event, AgentEvent::Error(m) if m == "API key missing"));
    }

    #[test]
    fn parse_thinking_event() {
        let json = r#"{"type":"thinking","content":"Analyzing..."}"#;
        let event = AgentEvent::from_json(json).unwrap();
        assert!(matches!(event, AgentEvent::Thinking(s) if s == "Analyzing..."));
    }

    #[test]
    fn unknown_type_returns_error() {
        let json = r#"{"type":"unknown"}"#;
        assert!(AgentEvent::from_json(json).is_err());
    }
}
