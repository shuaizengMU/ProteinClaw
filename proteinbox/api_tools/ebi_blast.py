import time
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

EBI_BLAST_BASE = "https://www.ebi.ac.uk/Tools/services/rest/ncbiblast"

# EBI BLAST only accepts these discrete values for alignments/scores.
_ALLOWED_HITS = (5, 10, 20, 50, 100, 150, 200, 250, 500, 750, 1000)


def _nearest_allowed_hits(n: int) -> int:
    """Round up to the nearest value accepted by EBI BLAST alignments/scores."""
    for v in _ALLOWED_HITS:
        if v >= n:
            return v
    return _ALLOWED_HITS[-1]


PROGRAM_STYPE = {
    "blastp": "protein",
    "blastn": "dna",
    "tblastn": "protein",
    "blastx": "dna",
    "tblastx": "dna",
}


@register_tool
class EBIBlastTool(ProteinTool):
    name: str = "ebi_blast"
    description: str = (
        "Run a BLAST search via the EBI JDispatcher NCBI BLAST REST service. "
        "Supports blastp, blastn, tblastn, blastx, tblastx and configurable target databases "
        "(e.g. uniprotkb, uniprotkb_swissprot, em_rel_pln for EMBL plants, ena_std). "
        "Returns aligned hits including each hit's identifier, description, E-value, "
        "identity, and the aligned hit sequence. Useful for cross-species or cross-accession "
        "ortholog retrieval when NCBI's blastp-against-nr is not the right target."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": "Query sequence (plain or FASTA). Protein for blastp/tblastn, nucleotide for blastn/blastx/tblastx.",
            },
            "program": {
                "type": "string",
                "enum": ["blastp", "blastn", "tblastn", "blastx", "tblastx"],
                "description": "BLAST program. Default: blastp.",
                "default": "blastp",
            },
            "database": {
                "type": "string",
                "description": "Target database. Default: uniprotkb for protein programs, em_rel for nucleotide.",
            },
            "max_hits": {
                "type": "integer",
                "description": "Maximum number of hits to return (default: 10).",
                "default": 10,
            },
            "evalue": {
                "type": "string",
                "description": "E-value threshold (default: 1e-5).",
                "default": "1e-5",
            },
            "email": {
                "type": "string",
                "description": "Contact email required by EBI JDispatcher. Default: proteinclaw@example.com.",
                "default": "proteinclaw@example.com",
            },
        },
        "required": ["sequence"],
    }

    def run(self, **kwargs) -> ToolResult:
        sequence = kwargs["sequence"].strip()
        program = kwargs.get("program", "blastp").strip().lower()
        if program not in PROGRAM_STYPE:
            return ToolResult(success=False, error=f"Unknown BLAST program: {program}")

        stype = PROGRAM_STYPE[program]
        default_db = "uniprotkb" if stype == "protein" else "em_rel"
        database = (kwargs.get("database") or default_db).strip()
        max_hits = int(kwargs.get("max_hits", 10))
        evalue = str(kwargs.get("evalue", "1e-5"))
        email = (kwargs.get("email") or "proteinclaw@example.com").strip()
        timeout = int(kwargs.get("timeout", 600))
        poll_interval = float(kwargs.get("poll_interval", 5.0))

        if sequence.startswith(">"):
            query = sequence
        else:
            query = ">query\n" + sequence

        try:
            job_id = self._submit(
                email=email,
                program=program,
                stype=stype,
                database=database,
                sequence=query,
                evalue=evalue,
                alignments=_nearest_allowed_hits(max_hits),
                scores=_nearest_allowed_hits(max_hits),
            )
        except Exception as e:
            return ToolResult(success=False, error=f"EBI BLAST submit failed: {e}")

        deadline = time.time() + timeout
        final_status = None
        while time.time() < deadline:
            time.sleep(poll_interval)
            try:
                status = self._status(job_id)
            except Exception as e:
                return ToolResult(success=False, error=f"EBI BLAST status check failed: {e}")
            if status == "FINISHED":
                final_status = status
                break
            if status in {"ERROR", "FAILURE", "NOT_FOUND"}:
                return ToolResult(success=False, error=f"EBI BLAST job {job_id} {status}")
        if final_status != "FINISHED":
            return ToolResult(success=False, error=f"EBI BLAST job {job_id} timed out after {timeout}s")

        try:
            hits = self._fetch_json_hits(job_id, max_hits)
        except Exception as e:
            return ToolResult(success=False, error=f"EBI BLAST result parse failed: {e}")

        display = (
            f"EBI BLAST ({program} vs {database}) job {job_id}: {len(hits)} hits"
            + (f". Top: {hits[0]['description'][:80]}" if hits else "")
        )
        return ToolResult(
            success=True,
            data={"job_id": job_id, "program": program, "database": database, "hits": hits},
            display=display,
        )

    def _submit(
        self,
        *,
        email: str,
        program: str,
        stype: str,
        database: str,
        sequence: str,
        evalue: str,
        alignments: int,
        scores: int,
    ) -> str:
        resp = httpx.post(
            f"{EBI_BLAST_BASE}/run",
            data={
                "email": email,
                "program": program,
                "stype": stype,
                "database": database,
                "sequence": sequence,
                "exp": evalue,
                "alignments": str(alignments),
                "scores": str(scores),
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.text.strip()

    def _status(self, job_id: str) -> str:
        resp = httpx.get(f"{EBI_BLAST_BASE}/status/{job_id}", timeout=30)
        resp.raise_for_status()
        return resp.text.strip().upper()

    def _fetch_json_hits(self, job_id: str, max_hits: int) -> list[dict]:
        resp = httpx.get(f"{EBI_BLAST_BASE}/result/{job_id}/json", timeout=120)
        resp.raise_for_status()
        payload = resp.json()

        hits_out: list[dict] = []
        raw_hits = (
            (payload.get("hits") if isinstance(payload, dict) else None)
            or _nested_hits(payload)
            or []
        )
        for hit in raw_hits[:max_hits]:
            if not isinstance(hit, dict):
                continue
            hit_id = hit.get("hit_acc") or hit.get("hit_id") or hit.get("id", "")
            hit_desc = hit.get("hit_desc") or hit.get("hit_def") or hit.get("description", "")
            hit_len = hit.get("hit_len") or hit.get("length")
            hsps = hit.get("hit_hsps") or hit.get("hsps") or []
            if not hsps:
                continue
            top = hsps[0] if isinstance(hsps, list) else hsps
            align_len = int(top.get("hsp_align_len") or top.get("align_len") or 1)
            identity = int(top.get("hsp_identity") or top.get("identity") or 0)
            hits_out.append({
                "hit_id": hit_id,
                "description": hit_desc,
                "hit_length": hit_len,
                "evalue": top.get("hsp_expect") or top.get("evalue"),
                "bit_score": top.get("hsp_bit_score") or top.get("bit_score"),
                "identity_pct": round(identity / align_len * 100, 1) if align_len else None,
                "query_seq": top.get("hsp_qseq") or top.get("qseq", ""),
                "hit_seq": top.get("hsp_hseq") or top.get("hseq", ""),
                "midline": top.get("hsp_mseq") or top.get("midline", ""),
            })
        return hits_out


def _nested_hits(payload) -> list | None:
    if not isinstance(payload, dict):
        return None
    for key in ("hit", "Hit", "results"):
        val = payload.get(key)
        if isinstance(val, list):
            return val
    return None
