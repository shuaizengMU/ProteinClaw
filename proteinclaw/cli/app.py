from __future__ import annotations
import uvicorn
import typer

app = typer.Typer(help="ProteinClaw — AI agent for protein bioinformatics.")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to listen on"),
):
    """Start the ProteinClaw server (API + WebSocket)."""
    uvicorn.run("proteinclaw.server.main:app", host=host, port=port, reload=False)


def main() -> None:
    app()
