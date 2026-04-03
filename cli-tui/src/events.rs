use serde::Deserialize;
use serde_json::Value;

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WsEvent {
    Token { content: String },
    Thinking { content: String },
    ToolCall { tool: String, args: Value },
    Observation { #[allow(dead_code)] tool: String, result: Value },
    TokenUsage { input_tokens: u32, output_tokens: u32 },
    #[allow(dead_code)]
    Done,
    Error { message: String },
}
