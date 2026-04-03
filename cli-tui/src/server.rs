use anyhow::{Context, Result};
use std::process::{Child, Command, Stdio};
use std::time::Duration;

pub struct ServerHandle {
    child: Child,
}

impl Drop for ServerHandle {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

/// Spawn the Python uvicorn server on the given port.
pub fn spawn(port: u16) -> Result<ServerHandle> {
    let child = Command::new("uv")
        .args([
            "run",
            "uvicorn",
            "proteinclaw.server.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .context("Failed to spawn Python server. Is uv installed and are you in the project root?")?;
    Ok(ServerHandle { child })
}

/// Poll TCP until the server accepts connections, or time out after ~15 s.
pub async fn wait_ready(port: u16) -> Result<()> {
    use tokio::net::TcpStream;
    let addr = format!("127.0.0.1:{port}");
    for _ in 0..30 {
        if TcpStream::connect(&addr).await.is_ok() {
            // Small grace period for uvicorn to finish startup
            tokio::time::sleep(Duration::from_millis(300)).await;
            return Ok(());
        }
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
    anyhow::bail!("Python server did not start within 15 seconds on port {port}")
}
