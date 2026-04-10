import re
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

ENSEMBL_REST = "https://rest.ensembl.org"
TAIR_LOCUS_RE = re.compile(r"^AT[1-5CM]G\d{5}$", re.IGNORECASE)


@register_tool
class EnsemblPlantsTool(ProteinTool):
    name: str = "ensembl_plants"
    description: str = (
        "Fetch a reference plant gene and its canonical protein sequence from Ensembl REST "
        "(covers Ensembl Plants species such as Arabidopsis thaliana). "
        "Accepts a TAIR-style locus id like AT1G62630 or a gene symbol plus species. "
        "Returns the canonical protein sequence in FASTA format along with gene coordinates "
        "and transcript list — useful as the reference input for cross-accession comparisons."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "locus_id": {
                "type": "string",
                "description": "TAIR locus id, e.g. AT1G62630. Preferred for Arabidopsis thaliana.",
            },
            "symbol": {
                "type": "string",
                "description": "Gene symbol, used if locus_id is not provided.",
            },
            "species": {
                "type": "string",
                "description": "Ensembl species slug, e.g. arabidopsis_thaliana (default), oryza_sativa, zea_mays.",
                "default": "arabidopsis_thaliana",
            },
        },
    }

    def run(self, **kwargs) -> ToolResult:
        locus_id = (kwargs.get("locus_id") or "").strip()
        symbol = (kwargs.get("symbol") or "").strip()
        species = (kwargs.get("species") or "arabidopsis_thaliana").strip().lower()

        if not locus_id and not symbol:
            return ToolResult(success=False, error="Provide locus_id or symbol")

        headers = {"Accept": "application/json"}

        try:
            if locus_id:
                lookup_url = f"{ENSEMBL_REST}/lookup/id/{locus_id}"
            else:
                lookup_url = f"{ENSEMBL_REST}/lookup/symbol/{species}/{symbol}"
            resp = httpx.get(lookup_url, params={"expand": "1"}, headers=headers, timeout=30)
            if resp.status_code != 200:
                target = locus_id or f"{symbol} in {species}"
                return ToolResult(success=False, error=f"Ensembl Plants: '{target}' not found")
            gene = resp.json()
        except Exception as e:
            return ToolResult(success=False, error=f"Ensembl Plants lookup failed: {e}")

        gene_id = gene.get("id", "")
        transcripts = gene.get("Transcript", []) or []
        canonical = next(
            (t for t in transcripts if t.get("is_canonical", 0) == 1),
            transcripts[0] if transcripts else None,
        )
        if canonical is None:
            return ToolResult(success=False, error=f"Ensembl Plants: no transcripts for {gene_id}")

        protein_id = ""
        translation = canonical.get("Translation") or {}
        if isinstance(translation, dict):
            protein_id = translation.get("id", "") or ""

        seq_id = protein_id or canonical.get("id", "")
        seq_type = "protein" if protein_id else "protein"

        try:
            seq_resp = httpx.get(
                f"{ENSEMBL_REST}/sequence/id/{seq_id}",
                params={"type": seq_type},
                headers=headers,
                timeout=30,
            )
            if seq_resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"Ensembl Plants: sequence fetch failed for {seq_id}",
                )
            seq_json = seq_resp.json()
        except Exception as e:
            return ToolResult(success=False, error=f"Ensembl Plants sequence fetch failed: {e}")

        sequence = (seq_json.get("seq") or "").replace("\n", "").strip()
        if not sequence:
            return ToolResult(success=False, error=f"Ensembl Plants: empty sequence for {seq_id}")

        fasta_header = f">{gene.get('display_name') or gene_id}_{gene.get('species', species)} {gene_id}"
        fasta = fasta_header + "\n" + _wrap_fasta(sequence)

        data = {
            "gene_id": gene_id,
            "display_name": gene.get("display_name", ""),
            "description": gene.get("description", ""),
            "biotype": gene.get("biotype", ""),
            "species": gene.get("species", species),
            "assembly": gene.get("assembly_name", ""),
            "chromosome": gene.get("seq_region_name", ""),
            "start": gene.get("start"),
            "end": gene.get("end"),
            "strand": gene.get("strand"),
            "canonical_transcript_id": canonical.get("id", ""),
            "protein_id": protein_id,
            "protein_length": len(sequence),
            "protein_sequence": sequence,
            "fasta": fasta,
            "transcripts": [
                {
                    "transcript_id": t.get("id", ""),
                    "biotype": t.get("biotype", ""),
                    "is_canonical": t.get("is_canonical", 0) == 1,
                    "length": t.get("length"),
                }
                for t in transcripts[:10]
            ],
        }

        display = (
            f"{data['display_name'] or gene_id} ({gene_id}) — {data['species']}, "
            f"Chr{data['chromosome']}:{data['start']}-{data['end']}, "
            f"canonical {canonical.get('id', '')}, protein {len(sequence)} aa"
        )
        return ToolResult(success=True, data=data, display=display)


def _wrap_fasta(seq: str, width: int = 60) -> str:
    return "\n".join(seq[i : i + width] for i in range(0, len(seq), width))
