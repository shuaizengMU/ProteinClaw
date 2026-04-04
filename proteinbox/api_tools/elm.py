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
                url = f"http://elm.eu.org/api/search/{seq_input}.json"
            else:
                seq = "".join(c for c in seq_input.upper() if c.isalpha())
                url = f"http://elm.eu.org/api/search/{seq}.json"

            resp = httpx.get(
                url,
                headers={
                    "Accept": "application/json",
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

            data = resp.json()
            instances = data if isinstance(data, list) else data.get("instances", data.get("matches", []))

            motifs = []
            class_counts: dict[str, int] = {}
            for inst in (instances if isinstance(instances, list) else [])[:30]:
                elm_id = inst.get("elm_identifier", inst.get("motif_name", ""))
                motif_class = elm_id.split("_")[0] if "_" in elm_id else elm_id[:3]
                class_counts[motif_class] = class_counts.get(motif_class, 0) + 1

                motifs.append({
                    "elm_identifier": elm_id,
                    "motif_class": motif_class,
                    "start": inst.get("start", inst.get("start_position", "")),
                    "end": inst.get("end", inst.get("end_position", "")),
                    "sequence_match": inst.get("sequence", inst.get("match", "")),
                    "description": inst.get("description", inst.get("functional_site_description", "")),
                    "regex": inst.get("regex", inst.get("pattern", "")),
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
