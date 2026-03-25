// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::Manager;

struct PythonServer(Arc<Mutex<Option<Child>>>);

fn find_free_port(start: u16) -> u16 {
    for port in start..65535 {
        if std::net::TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return port;
        }
    }
    panic!("No free port found");
}

fn venv_exists(app_data_dir: &PathBuf) -> bool {
    app_data_dir.join("venv").join("pyvenv.cfg").exists()
}

fn uv_binary_path(resource_dir: &PathBuf) -> PathBuf {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    return resource_dir.join("binaries").join("uv-aarch64-apple-darwin");
    #[cfg(all(target_os = "macos", target_arch = "x86_64"))]
    return resource_dir.join("binaries").join("uv-x86_64-apple-darwin");
    #[cfg(target_os = "windows")]
    return resource_dir.join("binaries").join("uv-x86_64-pc-windows-msvc.exe");
}

fn poll_health(port: u16, timeout_secs: u64) -> bool {
    let url = format!("http://127.0.0.1:{}/health", port);
    let deadline = std::time::Instant::now() + Duration::from_secs(timeout_secs);
    while std::time::Instant::now() < deadline {
        if let Ok(resp) = ureq::get(&url).call() {
            if resp.status() == 200 {
                return true;
            }
        }
        thread::sleep(Duration::from_secs(1));
    }
    false
}

fn start_python_server(
    uv: &PathBuf,
    project_dir: &PathBuf,
    venv_dir: &PathBuf,
    port: u16,
) -> std::io::Result<Child> {
    Command::new(uv)
        .args([
            "run",
            "--project", project_dir.to_str().unwrap_or_default(),
            "--venv", venv_dir.to_str().unwrap_or_default(),
            "uvicorn",
            "proteinclaw.server.main:app",
            "--host", "127.0.0.1",
            "--port", &port.to_string(),
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let resource_dir = app.path().resource_dir().expect("resource dir");
            let app_data_dir = app.path().app_data_dir().expect("app data dir");
            let venv_dir = app_data_dir.join("venv");
            let uv = uv_binary_path(&resource_dir);
            let port = find_free_port(8000);

            // First-launch: create venv if absent
            if !venv_exists(&app_data_dir) {
                // TODO: show splash window here (future enhancement)
                let status = Command::new(&uv)
                    .args([
                        "sync",
                        "--project", resource_dir.to_str().unwrap_or_default(),
                        "--venv", venv_dir.to_str().unwrap_or_default(),
                    ])
                    .status()
                    .expect("failed to spawn uv sync");
                if !status.success() {
                    eprintln!("uv sync failed with exit code: {:?}", status.code());
                    std::process::exit(1);
                }
            }

            // Start Python server — retry up to 3 times before giving up
            let mut child: Option<Child> = None;
            for attempt in 1..=4 {
                match start_python_server(&uv, &resource_dir, &venv_dir, port) {
                    Ok(c) => {
                        if poll_health(port, 30) {
                            child = Some(c);
                            break;
                        }
                        // Server started but didn't become healthy — kill and retry
                        let mut c = c;
                        let _ = c.kill();
                    }
                    Err(e) => {
                        eprintln!("Attempt {}: failed to start Python server: {}", attempt, e);
                    }
                }
                if attempt == 4 {
                    // All retries exhausted — exit with a visible error
                    // (Native dialog deferred; eprintln is the minimum contract)
                    eprintln!("Python server failed to start after 4 attempts. Check logs.");
                    std::process::exit(1);
                }
                thread::sleep(Duration::from_secs(2));
            }

            let child = child.expect("child must be set if we reach here");
            let server_guard = Arc::new(Mutex::new(Some(child)));
            app.manage(PythonServer(server_guard.clone()));

            // Kill server on app exit
            let sg = server_guard.clone();
            if let Some(win) = app.get_webview_window("main") {
                win.on_window_event(move |event| {
                    if let tauri::WindowEvent::Destroyed = event {
                        if let Ok(mut guard) = sg.lock() {
                            if let Some(mut child) = guard.take() {
                                let _ = child.kill();
                            }
                        }
                    }
                });
            }

            // Server is healthy — inject port and show the window
            // Window was created hidden (visible: false in tauri.conf.json),
            // so __BACKEND_PORT__ is set before any React code runs.
            if let Some(window) = app.get_webview_window("main") {
                let script = format!("window.__BACKEND_PORT__ = {};", port);
                window.eval(&script).expect("failed to inject __BACKEND_PORT__");
                if let Err(e) = window.show() {
                    eprintln!("Warning: failed to show window: {}", e);
                }
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Tauri application");
}
