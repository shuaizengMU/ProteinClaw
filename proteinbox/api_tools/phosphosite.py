import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class PhosphoSiteTool(ProteinTool):
    name: str = "phosphosite"
    description: str = (
        "Retrieve post-translational modification (PTM) sites for a protein from UniProt. "
        "Returns phosphorylation, ubiquitination, acetylation, methylation, and other modification sites "
        "with their positions, types, and evidence. Useful for understanding protein regulation."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "accession_id": {
                "type": "string",
                "description": "UniProt accession ID (e.g. P04637 for TP53)",
            },
        },
        "required": ["accession_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        accession = kwargs["accession_id"].strip().upper()

        try:
            # Fetch UniProt features (PTM annotations)
            resp = httpx.get(
                f"https://rest.uniprot.org/uniprotkb/{accession}.json",
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"UniProt returned {resp.status_code} for {accession}")

            raw = resp.json()
            protein_name = (
                raw.get("proteinDescription", {})
                .get("recommendedName", {})
                .get("fullName", {})
                .get("value", "Unknown")
            )

            ptm_types = {
                "Modified residue", "Lipidation", "Glycosylation",
                "Disulfide bond", "Cross-link",
            }

            modifications = []
            for feat in raw.get("features", []):
                ftype = feat.get("type", "")
                if ftype in ptm_types:
                    loc = feat.get("location", {})
                    start = loc.get("start", {}).get("value")
                    end = loc.get("end", {}).get("value")
                    desc = feat.get("description", "")
                    evidence = [
                        e.get("code", "")
                        for e in feat.get("evidences", [])
                    ]

                    modifications.append({
                        "type": ftype,
                        "position": f"{start}" if start == end else f"{start}-{end}",
                        "description": desc,
                        "evidence": evidence[:3],
                    })

            # Group by type for summary
            type_counts = {}
            for m in modifications:
                t = m["type"]
                type_counts[t] = type_counts.get(t, 0) + 1

            # Also extract PTM comments
            ptm_comments = [
                t["value"]
                for c in raw.get("comments", [])
                if c.get("commentType") == "PTM"
                for t in c.get("texts", [])
            ]

            data = {
                "accession": accession,
                "protein_name": protein_name,
                "total_ptms": len(modifications),
                "type_summary": type_counts,
                "modifications": modifications[:30],
                "ptm_comments": ptm_comments,
            }

            summary_parts = [f"{v} {k}" for k, v in type_counts.items()]
            display = (
                f"{protein_name} ({accession}): {len(modifications)} PTM sites — "
                + ", ".join(summary_parts) if summary_parts else "no PTM sites annotated"
            )
            return ToolResult(success=True, data=data, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
