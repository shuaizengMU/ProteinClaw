import time
import re
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

CLUSTALO_BASE = "https://www.ebi.ac.uk/Tools/services/rest/clustalo"


@register_tool
class ClustalOmegaTool(ProteinTool):
    name: str = "clustal_omega"
    description: str = (
        "Run a multiple sequence alignment via the EBI JDispatcher Clustal Omega REST service. "
        "Input is a multi-FASTA string containing two or more sequences. Returns the aligned "
        "sequences (as a dict mapping sequence id to aligned sequence), the Clustal-format "
        "alignment text, alignment length, and simple conservation stats (column-level identity). "
        "Useful for comparing a reference protein against orthologs from multiple accessions."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "sequences": {
                "type": "string",
                "description": "Multi-FASTA string with 2+ sequences. Each record must start with '>'.",
            },
            "stype": {
                "type": "string",
                "enum": ["protein", "dna", "rna"],
                "description": "Sequence type. Default: protein.",
                "default": "protein",
            },
            "email": {
                "type": "string",
                "description": "Contact email required by EBI JDispatcher. Default: proteinclaw@example.com.",
                "default": "proteinclaw@example.com",
            },
        },
        "required": ["sequences"],
    }

    def run(self, **kwargs) -> ToolResult:
        sequences = kwargs["sequences"]
        if not isinstance(sequences, str) or sequences.count(">") < 2:
            return ToolResult(
                success=False,
                error="clustal_omega requires a multi-FASTA string with at least 2 sequences",
            )
        stype = (kwargs.get("stype") or "protein").strip().lower()
        email = (kwargs.get("email") or "proteinclaw@example.com").strip()
        timeout = int(kwargs.get("timeout", 300))
        poll_interval = float(kwargs.get("poll_interval", 5.0))

        try:
            job_id = self._submit(email=email, stype=stype, sequence=sequences)
        except Exception as e:
            return ToolResult(success=False, error=f"Clustal Omega submit failed: {e}")

        deadline = time.time() + timeout
        final_status = None
        while time.time() < deadline:
            time.sleep(poll_interval)
            try:
                status = self._status(job_id)
            except Exception as e:
                return ToolResult(success=False, error=f"Clustal Omega status check failed: {e}")
            if status == "FINISHED":
                final_status = status
                break
            if status in {"ERROR", "FAILURE", "NOT_FOUND"}:
                return ToolResult(success=False, error=f"Clustal Omega job {job_id} {status}")
        if final_status != "FINISHED":
            return ToolResult(
                success=False,
                error=f"Clustal Omega job {job_id} timed out after {timeout}s",
            )

        try:
            clustal_text = self._fetch_result(job_id)
        except Exception as e:
            return ToolResult(success=False, error=f"Clustal Omega result fetch failed: {e}")

        aligned = _parse_clustal(clustal_text)
        if not aligned:
            return ToolResult(success=False, error="Clustal Omega returned an unparseable alignment")

        align_len = len(next(iter(aligned.values())))
        conserved_cols = _count_conserved_columns(aligned)
        identity_pct = round(conserved_cols / align_len * 100, 1) if align_len else 0.0

        display = (
            f"Clustal Omega job {job_id}: {len(aligned)} sequences, "
            f"alignment length {align_len}, {conserved_cols} fully conserved columns "
            f"({identity_pct}%)"
        )
        return ToolResult(
            success=True,
            data={
                "job_id": job_id,
                "aligned": aligned,
                "clustal": clustal_text,
                "alignment_length": align_len,
                "num_sequences": len(aligned),
                "conserved_columns": conserved_cols,
                "column_identity_pct": identity_pct,
            },
            display=display,
        )

    def _submit(self, *, email: str, stype: str, sequence: str) -> str:
        resp = httpx.post(
            f"{CLUSTALO_BASE}/run",
            data={"email": email, "stype": stype, "sequence": sequence},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.text.strip()

    def _status(self, job_id: str) -> str:
        resp = httpx.get(f"{CLUSTALO_BASE}/status/{job_id}", timeout=30)
        resp.raise_for_status()
        return resp.text.strip().upper()

    def _fetch_result(self, job_id: str) -> str:
        resp = httpx.get(f"{CLUSTALO_BASE}/result/{job_id}/aln-clustal_num", timeout=120)
        resp.raise_for_status()
        return resp.text


_CLUSTAL_LINE = re.compile(r"^(\S+)\s+([A-Za-z\-\.]+)(?:\s+\d+)?\s*$")


def _parse_clustal(text: str) -> dict[str, str]:
    aligned: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.startswith("CLUSTAL") or line.startswith(" "):
            continue
        m = _CLUSTAL_LINE.match(line)
        if not m:
            continue
        name, chunk = m.group(1), m.group(2)
        aligned[name] = aligned.get(name, "") + chunk
    return aligned


def _count_conserved_columns(aligned: dict[str, str]) -> int:
    if not aligned:
        return 0
    seqs = list(aligned.values())
    length = len(seqs[0])
    count = 0
    for i in range(length):
        col = {s[i] for s in seqs}
        if len(col) == 1 and "-" not in col:
            count += 1
    return count
