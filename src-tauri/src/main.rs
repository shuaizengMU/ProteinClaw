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

fn venv_is_current(app_data_dir: &PathBuf, current_version: &str) -> bool {
    if !app_data_dir.join("venv").join("pyvenv.cfg").exists() {
        return false;
    }
    match std::fs::read_to_string(app_data_dir.join("venv_version.txt")) {
        Ok(v) => v.trim() == current_version,
        Err(_) => false,
    }
}

/// Recursively copy a file or directory to dst.
fn copy_path(src: &PathBuf, dst: &PathBuf) {
    if src.is_dir() {
        std::fs::create_dir_all(dst).expect("failed to create dst dir");
        for entry in std::fs::read_dir(src).expect("failed to read src dir") {
            let entry = entry.expect("failed to read dir entry");
            copy_path(&entry.path(), &dst.join(entry.file_name()));
        }
    } else {
        std::fs::copy(src, dst).expect("cp file failed");
    }
}

fn uv_binary_path() -> PathBuf {
    // Tauri places external binaries alongside the main executable (Contents/MacOS/ on macOS),
    // stripping the target-triple suffix used in src-tauri/binaries/.
    let exe_dir = std::env::current_exe()
        .expect("cannot get exe path")
        .parent()
        .expect("exe has no parent")
        .to_path_buf();
    #[cfg(target_os = "windows")]
    return exe_dir.join("uv.exe");
    #[cfg(not(target_os = "windows"))]
    return exe_dir.join("uv");
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
    venv_dir: &PathBuf,
    port: u16,
) -> std::io::Result<Child> {
    // Use the venv Python directly — avoids uv trying to re-sync on every launch.
    #[cfg(target_os = "windows")]
    let python = venv_dir.join("Scripts").join("python.exe");
    #[cfg(not(target_os = "windows"))]
    let python = venv_dir.join("bin").join("python");

    Command::new(python)
        .args([
            "-m", "uvicorn",
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
            let uv = uv_binary_path();
            let port = find_free_port(8000);
            let current_version = app.package_info().version.to_string();

            // Create or rebuild venv when missing or when the app version has changed.
            // We copy the project files to a writable temp dir before running uv sync
            // because the .app bundle is read-only on macOS — setuptools needs to write
            // {pkg}.egg-info into the project directory during the build step.
            if !venv_is_current(&app_data_dir, &current_version) {
                // Remove stale venv so uv sync starts clean.
                let _ = std::fs::remove_dir_all(&venv_dir);
                let tmp_project = std::env::temp_dir().join("proteinclaw-setup");
                let _ = std::fs::remove_dir_all(&tmp_project);
                std::fs::create_dir_all(&tmp_project).expect("create tmp project dir");
                for item in ["pyproject.toml", "uv.lock", "proteinclaw", "proteinbox"] {
                    let src = resource_dir.join(item);
                    if src.exists() {
                        copy_path(&src, &tmp_project.join(item));
                    }
                }

                let status = Command::new(&uv)
                    .env("UV_PROJECT_ENVIRONMENT", venv_dir.to_str().unwrap_or_default())
                    .args([
                        "sync",
                        "--no-editable",
                        "--project", tmp_project.to_str().unwrap_or_default(),
                    ])
                    .status()
                    .expect("failed to spawn uv sync");
                let _ = std::fs::remove_dir_all(&tmp_project);
                if !status.success() {
                    eprintln!("uv sync failed with exit code: {:?}", status.code());
                    std::process::exit(1);
                }
                // Record the version so future launches skip re-sync unless the app updates.
                std::fs::write(app_data_dir.join("venv_version.txt"), &current_version)
                    .expect("failed to write venv_version.txt");
            }

            // Start Python server — retry up to 3 times before giving up
            let mut child: Option<Child> = None;
            for attempt in 1..=4 {
                match start_python_server(&venv_dir, port) {
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
