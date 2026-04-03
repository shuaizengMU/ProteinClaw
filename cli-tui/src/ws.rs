use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use serde_json::{json, Value};
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite::Message};

use crate::events::WsEvent;

/// Commands sent from the UI to the WebSocket task.
pub enum WsCmd {
    Send {
        message: String,
        history: Vec<Value>,
        model: String,
    },
}

/// Events emitted by the WebSocket task back to the main loop.
pub enum WsAppEvent {
    Connected,
    Disconnected,
    Event(WsEvent),
    Error(String),
}

/// Long-running task: owns the WebSocket connection.
/// Forwards incoming events to `event_tx` and outgoing commands from `cmd_rx`.
pub async fn run(
    port: u16,
    event_tx: mpsc::UnboundedSender<WsAppEvent>,
    mut cmd_rx: mpsc::UnboundedReceiver<WsCmd>,
) {
    let url = format!("ws://127.0.0.1:{port}/ws/chat");

    let (ws_stream, _) = match connect_async(&url).await {
        Ok(s) => s,
        Err(e) => {
            let _ = event_tx.send(WsAppEvent::Error(format!("WS connect failed: {e}")));
            return;
        }
    };

    let _ = event_tx.send(WsAppEvent::Connected);
    let (mut write, mut read) = ws_stream.split();

    loop {
        tokio::select! {
            // Outgoing: send commands from UI
            cmd = cmd_rx.recv() => {
                match cmd {
                    Some(WsCmd::Send { message, history, model }) => {
                        let payload = json!({
                            "message": message,
                            "history": history,
                            "model": model,
                        });
                        if let Err(e) = write.send(Message::Text(payload.to_string().into())).await {
                            let _ = event_tx.send(WsAppEvent::Error(format!("WS send error: {e}")));
                        }
                    }
                    None => break, // cmd channel closed → quit
                }
            }

            // Incoming: forward server events
            msg = read.next() => {
                match msg {
                    Some(Ok(Message::Text(text))) => {
                        match serde_json::from_str::<WsEvent>(&text) {
                            Ok(ev) => { let _ = event_tx.send(WsAppEvent::Event(ev)); }
                            Err(_) => {} // ignore unknown event shapes
                        }
                    }
                    Some(Ok(_)) => {} // binary / ping / pong — ignore
                    None | Some(Err(_)) => {
                        let _ = event_tx.send(WsAppEvent::Disconnected);
                        break;
                    }
                }
            }
        }
    }
}

/// Helper: build the WsCmd::Send payload and dispatch it.
pub fn send_message(
    tx: &mpsc::UnboundedSender<WsCmd>,
    message: String,
    history: Vec<Value>,
    model: String,
) -> Result<()> {
    tx.send(WsCmd::Send {
        message,
        history,
        model,
    })?;
    Ok(())
}
