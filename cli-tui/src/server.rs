use anyhow::Result;
use std::process::{Child, Command, Stdio};
use tokio::net::TcpStream;
use tokio::time::{sleep, Duration};

pub struct ServerHandle(Option<Child>);

impl Drop for ServerHandle {
    fn drop(&mut self) {
        if let Some(child) = &mut self.0 {
            let _ = child.kill();
        }
    }
}

/// Spawn the Python backend, or return a no-op handle if `PROTEINCLAW_NO_SPAWN=1`.
///
/// Set `PROTEINCLAW_NO_SPAWN=1` when running the server manually in a separate
/// terminal — the TUI will skip spawning and just wait for the port to be ready.
///
/// Set `PROTEINCLAW_SERVER_CMD=<binary>` to override which command is used.
///
/// In debug builds the server's stderr is written to `server.log` in the
/// current directory so startup errors are visible after the TUI exits.
pub fn spawn(port: u16) -> Result<ServerHandle> {
    // No-spawn mode: user manages the server themselves.
    if std::env::var("PROTEINCLAW_NO_SPAWN").as_deref() == Ok("1") {
        return Ok(ServerHandle(None));
    }

    let port_str = port.to_string();
    let server_args = ["server", "--host", "127.0.0.1", "--port", &port_str];
    let stderr = server_stderr();

    // Allow the caller to override the command via env var (useful in dev/CI).
    if let Ok(cmd) = std::env::var("PROTEINCLAW_SERVER_CMD") {
        let child = Command::new(&cmd)
            .args(&server_args)
            .stdout(Stdio::null())
            .stderr(stderr)
            .spawn()
            .map_err(|e| anyhow::anyhow!("PROTEINCLAW_SERVER_CMD={cmd:?}: {e}"))?;
        return Ok(ServerHandle(Some(child)));
    }

    // Try candidates in order: installed binary → uv run → python3 -m.
    // `uv run proteinclaw` works in the project directory without installing.
    // `python3 -m proteinclaw` works if the package is on PYTHONPATH.
    let candidates: &[(&str, &[&str])] = &[
        ("proteinclaw", &[]),
        ("uv", &["run", "proteinclaw"]),
        ("python3", &["-m", "proteinclaw"]),
    ];

    let mut last_err = String::new();
    for (bin, prefix) in candidates {
        let args: Vec<&str> = prefix
            .iter()
            .copied()
            .chain(server_args.iter().copied())
            .collect();
        match Command::new(bin)
            .args(&args)
            .stdout(Stdio::null())
            .stderr(server_stderr())
            .spawn()
        {
            Ok(child) => return Ok(ServerHandle(Some(child))),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                last_err = format!("{bin}: {e}");
                continue;
            }
            Err(e) => return Err(anyhow::anyhow!("{bin}: {e}")),
        }
    }

    Err(anyhow::anyhow!(
        "Could not start the ProteinClaw Python server. \
         Tried: proteinclaw, uv run proteinclaw, python3 -m proteinclaw. \
         Last error: {last_err}. \
         Install with `uv tool install .` or set PROTEINCLAW_SERVER_CMD.\n\
         Tip: run the server manually and set PROTEINCLAW_NO_SPAWN=1."
    ))
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
    anyhow::bail!(
        "Server did not start within 10 seconds (port {port}).\n\
         Check server.log for errors, or run the server manually:\n\
         \n  uv run proteinclaw server --host 127.0.0.1 --port {port}\n\
         \nThen set PROTEINCLAW_NO_SPAWN=1 and restart the TUI."
    )
}

/// In debug builds: write server stderr to server.log so startup errors survive
/// after the alternate-screen TUI clears the terminal.
/// In release builds: discard stderr to keep the user experience clean.
fn server_stderr() -> Stdio {
    #[cfg(debug_assertions)]
    {
        if let Ok(f) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open("server.log")
        {
            use std::os::unix::io::IntoRawFd;
            return unsafe { Stdio::from_raw_fd(f.into_raw_fd()) };
        }
    }
    Stdio::null()
}

// Needed for the cfg(debug_assertions) block above.
#[cfg(debug_assertions)]
use std::os::unix::io::FromRawFd;
