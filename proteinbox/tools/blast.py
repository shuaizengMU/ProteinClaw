import time
import re
import xml.etree.ElementTree as ET
import httpx
from typing import Optional
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

BLAST_URL = "https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi"


@register_tool
class BLASTTool(ProteinTool):
    name: str = "blast"
    description: str = (
        "Run a BLAST search to find homologous proteins for a given sequence. "
        "Input is a protein sequence (plain amino acids or FASTA format). "
        "Returns top hits with descriptions, accessions, E-values, and identity."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": "Protein sequence in plain amino acids or FASTA format",
            },
            "max_hits": {
                "type": "integer",
                "description": "Maximum number of hits to return (default: 5)",
                "default": 5,
            },
        },
        "required": ["sequence"],
    }

    def run(self, **kwargs) -> ToolResult:
        sequence: str = kwargs["sequence"].strip()
        max_hits: int = int(kwargs.get("max_hits", 5))
        timeout: int = int(kwargs.get("timeout", 120))
        poll_interval: float = float(kwargs.get("poll_interval", 5.0))

        # Strip FASTA header if present
        if sequence.startswith(">"):
            sequence = "\n".join(sequence.split("\n")[1:])

        # Submit job
        try:
            rid, estimated_time = self._submit(sequence)
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"BLAST submit failed: {e}")

        # Poll for results
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(poll_interval)
            status = self._check_status(rid)
            if status == "READY":
                break
            if status == "FAILED":
                return ToolResult(success=False, data=None, error="BLAST search failed on NCBI side")
        else:
            return ToolResult(success=False, data=None, error=f"BLAST search timed out after {timeout}s")

        # Fetch results
        try:
            hits = self._fetch_results(rid, max_hits)
        except Exception as e:
            return ToolResult(success=False, data=None, error=f"BLAST result parse failed: {e}")

        display = f"BLAST found {len(hits)} hits. Top: {hits[0]['description'][:100] if hits else 'none'}"
        return ToolResult(success=True, data={"hits": hits, "rid": rid}, display=display)

    def _submit(self, sequence: str) -> tuple[str, int]:
        resp = httpx.post(
            BLAST_URL,
            data={
                "CMD": "Put",
                "PROGRAM": "blastp",
                "DATABASE": "nr",
                "QUERY": sequence,
                "FORMAT_TYPE": "XML",
            },
            timeout=30,
        )
        resp.raise_for_status()
        rid_match = re.search(r"RID\s*=\s*(\S+)", resp.text)
        rtoe_match = re.search(r"RTOE\s*=\s*(\d+)", resp.text)
        if not rid_match:
            raise ValueError("Could not parse RID from BLAST submit response")
        return rid_match.group(1), int(rtoe_match.group(1)) if rtoe_match else 10

    def _check_status(self, rid: str) -> str:
        resp = httpx.get(
            BLAST_URL,
            params={"CMD": "Get", "RID": rid, "FORMAT_OBJECT": "SearchInfo"},
            timeout=15,
        )
        if "Status=READY" in resp.text:
            return "READY"
        if "Status=FAILED" in resp.text or "Status=UNKNOWN" in resp.text:
            return "FAILED"
        return "WAITING"

    def _fetch_results(self, rid: str, max_hits: int) -> list[dict]:
        resp = httpx.get(
            BLAST_URL,
            params={"CMD": "Get", "RID": rid, "FORMAT_TYPE": "XML"},
            timeout=60,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
        hits = []
        for hit in root.iter("Hit"):
            hsp = hit.find(".//Hsp")
            if hsp is None:
                continue
            align_len = int(hsp.findtext("Hsp_align-len") or 1)
            identity = int(hsp.findtext("Hsp_identity") or 0)
            hits.append({
                "description": hit.findtext("Hit_def", ""),
                "accession": hit.findtext("Hit_accession", ""),
                "evalue": hsp.findtext("Hsp_evalue", ""),
                "identity_pct": round(identity / align_len * 100, 1),
            })
            if len(hits) >= max_hits:
                break
        return hits
