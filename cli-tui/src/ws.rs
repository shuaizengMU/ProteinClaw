use crate::events::WsEvent;
use anyhow::Result;
use futures_util::{SinkExt, StreamExt};
use serde_json::Value;
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite::Message};

pub enum WsCmd {
    Send(String),
}

pub enum WsAppEvent {
    Connected,
    Disconnected,
    Event(WsEvent),
    Error(String),
}

pub async fn run(
    port: u16,
    event_tx: mpsc::UnboundedSender<WsAppEvent>,
    mut cmd_rx: mpsc::UnboundedReceiver<WsCmd>,
) {
    let url = format!("ws://127.0.0.1:{}/ws/chat", port);

    let ws_stream = match connect_async(&url).await {
        Ok((ws, _)) => ws,
        Err(e) => {
            let _ = event_tx.send(WsAppEvent::Error(format!("WS connect failed: {e}")));
            return;
        }
    };

    let _ = event_tx.send(WsAppEvent::Connected);
    let (mut sink, mut stream) = ws_stream.split();

    loop {
        tokio::select! {
            msg = stream.next() => {
                match msg {
                    Some(Ok(Message::Text(text))) => {
                        match serde_json::from_str::<WsEvent>(&text) {
                            Ok(ev) => { let _ = event_tx.send(WsAppEvent::Event(ev)); }
                            Err(_) => {} // unknown event type — silently ignore
                        }
                    }
                    Some(Ok(_)) => {}
                    Some(Err(e)) => {
                        let _ = event_tx.send(WsAppEvent::Error(format!("WS error: {e}")));
                        break;
                    }
                    None => {
                        let _ = event_tx.send(WsAppEvent::Disconnected);
                        break;
                    }
                }
            }
            cmd = cmd_rx.recv() => {
                match cmd {
                    Some(WsCmd::Send(payload)) => {
                        if let Err(e) = sink.send(Message::Text(payload)).await {
                            let _ = event_tx.send(WsAppEvent::Error(format!("Send failed: {e}")));
                        }
                    }
                    None => break,
                }
            }
        }
    }
}

pub fn send_message(
    cmd_tx: &mpsc::UnboundedSender<WsCmd>,
    text: String,
    history: Vec<Value>,
    model: String,
) -> Result<()> {
    let payload = serde_json::json!({
        "message": text,
        "model": model,
        "history": history,
    });
    cmd_tx
        .send(WsCmd::Send(payload.to_string()))
        .map_err(|e| anyhow::anyhow!("WS channel closed: {e}"))
}
