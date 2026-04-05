import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class ELMTool(ProteinTool):
    name: str = "elm"
    description: str = (
        "Search the Eukaryotic Linear Motif (ELM) resource for short linear motifs (SLiMs) "
        "in a protein sequence. Returns predicted functional motifs — binding sites, "
        "modification sites, docking motifs, and degradation signals. "
        "Especially useful for disordered protein regions."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "sequence": {
                "type": "string",
                "description": "Protein sequence (amino acid one-letter codes) or UniProt accession (e.g. P04637)",
            },
        },
        "required": ["sequence"],
    }

    def run(self, **kwargs) -> ToolResult:
        seq_input = kwargs["sequence"].strip()

        try:
            is_accession = len(seq_input) <= 20 and seq_input.replace("_", "").isalnum()

            if is_accession:
                query = seq_input
            else:
                query = "".join(c for c in seq_input.upper() if c.isalpha())

            resp = httpx.get(
                "http://elm.eu.org/instances.gff",
                params={"q": query},
                headers={
                    "User-Agent": "ProteinClaw/1.0 (bioinformatics tool)",
                },
                timeout=30,
                follow_redirects=True,
            )

            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=(
                        f"ELM returned {resp.status_code}. "
                        "The ELM server may be temporarily unavailable. "
                        "Try the web interface at http://elm.eu.org"
                    ),
                )

            # Parse GFF3 format: seqid source type start end score strand phase attributes
            motifs = []
            class_counts: dict[str, int] = {}
            for line in resp.text.splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                if line.startswith(">"):
                    break  # FASTA section starts
                parts = line.split("\t")
                if len(parts) < 9:
                    continue
                attrs = parts[8]
                elm_id = ""
                for attr in attrs.split(";"):
                    if attr.startswith("ID="):
                        elm_id = attr[3:]
                        break

                motif_class = elm_id.split("_")[0] if "_" in elm_id else elm_id[:3]
                class_counts[motif_class] = class_counts.get(motif_class, 0) + 1

                motifs.append({
                    "elm_identifier": elm_id,
                    "motif_class": motif_class,
                    "start": parts[3],
                    "end": parts[4],
                })

            class_labels = {
                "LIG": "ligand binding",
                "MOD": "modification",
                "DOC": "docking",
                "DEG": "degradation",
                "CLV": "cleavage",
                "TRG": "targeting",
            }
            class_strs = [
                f"{count} {class_labels.get(cls, cls)}"
                for cls, count in sorted(class_counts.items(), key=lambda x: -x[1])
            ]

            display = f"Found {len(motifs)} ELM motifs"
            if class_strs:
                display += ": " + ", ".join(class_strs[:6])

            return ToolResult(
                success=True,
                data={
                    "input": seq_input[:50],
                    "total_motifs": len(motifs),
                    "class_summary": class_counts,
                    "motifs": motifs,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
