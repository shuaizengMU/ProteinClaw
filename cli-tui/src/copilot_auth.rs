//! GitHub Copilot OAuth device-flow authentication.
//!
//! Flow:
//! 1. Request a device code from GitHub.
//! 2. User visits the verification URL and enters the user code.
//! 3. Poll GitHub until the user authorises → receive an OAuth access token.
//!
//! The OAuth token is saved to config. The Python backend exchanges it for a
//! short-lived Copilot session token on each LLM request.

use serde::Deserialize;

/// VS Code's Copilot client ID (public, used by all Copilot integrations).
const CLIENT_ID: &str = "Iv1.b507a08c87ecfe98";

#[derive(Debug, Deserialize)]
pub struct DeviceCodeResponse {
    pub device_code: String,
    pub user_code: String,
    pub verification_uri: String,
    pub interval: u64,
}

#[derive(Debug, Deserialize)]
struct PollResponse {
    access_token: Option<String>,
    error: Option<String>,
}

/// Step 1: Request a device code from GitHub.
pub async fn request_device_code() -> anyhow::Result<DeviceCodeResponse> {
    let client = reqwest::Client::new();
    let resp = client
        .post("https://github.com/login/device/code")
        .header("Accept", "application/json")
        .form(&[("client_id", CLIENT_ID), ("scope", "")])
        .send()
        .await?
        .json::<DeviceCodeResponse>()
        .await?;
    Ok(resp)
}

/// Step 2: Poll until the user authorises. Returns the OAuth access token.
pub async fn poll_for_token(device_code: &str, interval: u64) -> anyhow::Result<String> {
    let client = reqwest::Client::new();
    loop {
        tokio::time::sleep(std::time::Duration::from_secs(interval)).await;
        let resp: PollResponse = client
            .post("https://github.com/login/oauth/access_token")
            .header("Accept", "application/json")
            .form(&[
                ("client_id", CLIENT_ID),
                ("device_code", device_code),
                ("grant_type", "urn:ietf:params:oauth:grant-type:device_code"),
            ])
            .send()
            .await?
            .json()
            .await?;

        if let Some(token) = resp.access_token {
            return Ok(token);
        }
        match resp.error.as_deref() {
            Some("authorization_pending") => continue,
            Some("slow_down") => {
                tokio::time::sleep(std::time::Duration::from_secs(5)).await;
                continue;
            }
            Some(e) => anyhow::bail!("GitHub OAuth error: {}", e),
            None => continue,
        }
    }
}
