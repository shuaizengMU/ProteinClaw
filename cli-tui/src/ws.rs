use futures_util::{SinkExt, StreamExt};
use tokio::sync::mpsc::Sender;
use tokio_tungstenite::{connect_async, tungstenite::Message};

use crate::events::{AgentEvent, AppEvent};

/// Connect to the WebSocket server and return a channel for sending queries.
/// WS frames are deserialized and forwarded to `event_tx` as `AppEvent::WsMessage`.
pub async fn connect(port: u16, event_tx: Sender<AppEvent>) -> anyhow::Result<Sender<String>> {
    let url = format!("ws://127.0.0.1:{}/ws/chat", port);
    let (ws_stream, _) = connect_async(&url)
        .await
        .map_err(|e| anyhow::anyhow!("WebSocket connect failed: {}", e))?;

    let (mut write, mut read) = ws_stream.split();

    // Channel for outgoing messages (caller → writer task)
    let (ws_tx, mut ws_rx) = tokio::sync::mpsc::channel::<String>(32);

    // Writer task: forward strings from ws_rx to the WebSocket
    tokio::spawn(async move {
        while let Some(msg) = ws_rx.recv().await {
            if write.send(Message::Text(msg.into())).await.is_err() {
                break;
            }
        }
    });

    // Reader task: parse WS frames and forward as AppEvent
    tokio::spawn(async move {
        while let Some(frame) = read.next().await {
            match frame {
                Ok(Message::Text(text)) => {
                    match AgentEvent::from_json(&text) {
                        Ok(event) => {
                            let _ = event_tx.send(AppEvent::WsMessage(event)).await;
                        }
                        Err(_) => {} // ignore unparseable frames
                    }
                }
                Ok(Message::Close(_)) | Err(_) => {
                    let _ = event_tx
                        .send(AppEvent::WsError("Connection closed".into()))
                        .await;
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(ws_tx)
}
