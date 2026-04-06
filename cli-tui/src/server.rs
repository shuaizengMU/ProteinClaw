use anyhow::Result;
use std::process::{Child, Command, Stdio};
use tokio::net::TcpStream;
use tokio::time::{sleep, Duration};

pub struct ServerHandle(Child);

impl Drop for ServerHandle {
    fn drop(&mut self) {
        let _ = self.0.kill();
    }
}

pub fn spawn(port: u16) -> Result<ServerHandle> {
    // Use `proteinclaw server` (installed by uv tool install) rather than
    // `uvicorn` directly — uv tool install only exposes the package's own
    // entry-point scripts, not dependency binaries like uvicorn.
    let child = Command::new("proteinclaw")
        .args([
            "server",
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()?;
    Ok(ServerHandle(child))
}

pub async fn wait_ready(port: u16) -> Result<()> {
    let addr = format!("127.0.0.1:{}", port);
    for _ in 0..40 {
        if TcpStream::connect(&addr).await.is_ok() {
            // Brief pause for the server to finish binding
            sleep(Duration::from_millis(100)).await;
            return Ok(());
        }
        sleep(Duration::from_millis(250)).await;
    }
    anyhow::bail!("Server did not start within 10 seconds (port {})", port)
}
