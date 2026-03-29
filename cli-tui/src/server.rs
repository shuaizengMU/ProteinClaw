use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant};

pub struct ServerHandle {
    child: Child,
    pub port: u16,
}

impl Drop for ServerHandle {
    fn drop(&mut self) {
        let _ = self.child.kill();
    }
}

pub fn find_free_port(start: u16) -> u16 {
    (start..65000)
        .find(|&p| std::net::TcpListener::bind(("127.0.0.1", p)).is_ok())
        .expect("no free port found")
}

/// Start `python -m uvicorn proteinclaw.server.main:app` on a free port
/// and block until the port accepts TCP connections (max `timeout_secs`).
pub async fn start() -> anyhow::Result<ServerHandle> {
    let port = find_free_port(8000);
    let child = Command::new("python")
        .args([
            "-m", "uvicorn",
            "proteinclaw.server.main:app",
            "--host", "127.0.0.1",
            "--port", &port.to_string(),
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| anyhow::anyhow!("Failed to spawn Python server: {}. Is proteinclaw installed? Run: uv tool install proteinclaw", e))?;

    poll_tcp(port, 30).await?;
    Ok(ServerHandle { child, port })
}

async fn poll_tcp(port: u16, timeout_secs: u64) -> anyhow::Result<()> {
    let deadline = Instant::now() + Duration::from_secs(timeout_secs);
    loop {
        if tokio::net::TcpStream::connect(("127.0.0.1", port)).await.is_ok() {
            // Give uvicorn a moment to finish HTTP setup after TCP is open
            tokio::time::sleep(Duration::from_millis(300)).await;
            return Ok(());
        }
        if Instant::now() > deadline {
            anyhow::bail!("Python server did not start within {}s", timeout_secs);
        }
        tokio::time::sleep(Duration::from_millis(500)).await;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn find_free_port_returns_open_port() {
        let port = find_free_port(18000);
        let listener = std::net::TcpListener::bind(("127.0.0.1", port));
        assert!(listener.is_ok(), "port {} should be bindable", port);
    }

    #[test]
    fn find_free_port_skips_occupied() {
        let occupied = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
        let occupied_port = occupied.local_addr().unwrap().port();
        let next = find_free_port(occupied_port);
        assert_ne!(next, occupied_port);
    }
}
