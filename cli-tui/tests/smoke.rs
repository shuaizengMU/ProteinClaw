/// Verify the binary was built and exists.
/// Requires a prior `cargo build` to have produced the binary.
/// Set SKIP_SMOKE=1 to skip.
#[test]
fn binary_exists() {
    if std::env::var("SKIP_SMOKE").is_ok() {
        return;
    }

    let bin = env!("CARGO_BIN_EXE_proteinclaw-tui");
    assert!(std::path::Path::new(bin).exists(), "binary not found at {}", bin);
}
