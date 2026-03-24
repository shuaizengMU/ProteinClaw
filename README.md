# ProteinClaw

**An AI agent for protein bioinformatics — describe your research goal in plain English, get results.**

ProteinClaw accepts natural language queries, autonomously orchestrates protein analysis tools (UniProt, BLAST, and more), and streams a synthesized answer back to you. No scripting, no manual data wrangling between tools.

It runs on top of **ProteinBox**, a unified tool and database layer for protein science.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-24%20passed-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Demo

> Screenshot coming soon. See [Quick Start](#quick-start--docker-recommended) to run it yourself.

---

## Quick Start — Docker (recommended)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) and at least one LLM API key (e.g. OpenAI).

```bash
# 1. Clone the repo
git clone https://github.com/your-org/ProteinClaw.git
cd ProteinClaw

# 2. Set your API keys
cp .env.example .env
# Edit .env and fill in at least one key (e.g. OPENAI_API_KEY)

# 3. Start everything
docker compose up
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

Try asking: **"What is P04637?"** or **"Find homologs for this sequence: MEEPQSDPSVEPPLSQETFSDLWKLLPENN"**

---

## Quick Start — Local Python

**Prerequisites:** Python 3.11+, Node.js 20+

```bash
# Clone and install backend
git clone https://github.com/your-org/ProteinClaw.git
cd ProteinClaw
pip install -e ".[dev]"

# Set API keys
cp .env.example .env
# Edit .env and fill in at least one key

# Start backend
uvicorn proteinclaw.main:app --reload --port 8000

# In a separate terminal, start frontend
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## Usage

Type your research question in plain English. ProteinClaw will decide which tools to call, run them in sequence, and explain the results.

**Example queries:**

| Query | What happens |
|-------|-------------|
| `What is P04637?` | Fetches UniProt annotation for TP53 — function, GO terms, organism, sequence length |
| `Find proteins similar to this sequence: <FASTA>` | Submits a BLAST search and returns top hits with E-values and identity |
| `Tell me about the function of TP53 and find its homologs` | Chains UniProt + BLAST automatically |

**Switching models:** Use the dropdown in the top-right corner to choose your LLM. Your selection is remembered across sessions.

---

## Supported Models

| Model | Provider | API Key Required |
|-------|----------|-----------------|
| `gpt-4o` | OpenAI | `OPENAI_API_KEY` |
| `claude-opus-4-5` | Anthropic | `ANTHROPIC_API_KEY` |
| `deepseek-chat` | DeepSeek | `DEEPSEEK_API_KEY` |
| `deepseek-reasoner` | DeepSeek | `DEEPSEEK_API_KEY` |
| `minimax-text-01` | MiniMax | `MINIMAX_API_KEY` |
| `ollama/llama3` | Ollama (local) | None — run `docker compose --profile ollama up` |

You only need one key to get started.

---

## API Keys

Copy `.env.example` to `.env` and fill in the keys you need:

| Variable | Where to get it | Required |
|----------|----------------|----------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) | If using GPT-4o |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | If using Claude |
| `DEEPSEEK_API_KEY` | [platform.deepseek.com](https://platform.deepseek.com) | If using DeepSeek |
| `MINIMAX_API_KEY` | [api.minimax.chat](https://api.minimax.chat) | If using MiniMax |
| `NCBI_API_KEY` | [ncbi.nlm.nih.gov/account](https://www.ncbi.nlm.nih.gov/account/) | Optional — increases BLAST rate limit |

---

## Architecture

ProteinClaw consists of two layers: **ProteinBox** (tool registry — UniProt, BLAST, and future tools) and the **ProteinClaw agent** (a ReAct loop backed by LiteLLM for multi-model routing). The agent receives your query, decides which tools to call, runs them via a FastAPI backend, and streams results to a React frontend over WebSocket. See [`docs/superpowers/specs/2026-03-24-proteinclaw-design.md`](docs/superpowers/specs/2026-03-24-proteinclaw-design.md) for the full design.

---

## Contributing

Contributions are welcome — new tools, database integrations, and bug fixes especially. Please open an issue first to discuss what you'd like to add.

---

## License

MIT
