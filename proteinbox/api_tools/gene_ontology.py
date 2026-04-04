import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class GeneOntologyTool(ProteinTool):
    name: str = "gene_ontology"
    description: str = (
        "Retrieve Gene Ontology (GO) functional annotations for a protein from QuickGO. "
        "Returns GO terms grouped by aspect: molecular function, biological process, "
        "and cellular component. Useful for understanding what a protein does, where it acts, "
        "and which processes it participates in."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "accession": {
                "type": "string",
                "description": "UniProt accession ID (e.g. P04637 for TP53)",
            },
        },
        "required": ["accession"],
    }

    def run(self, **kwargs) -> ToolResult:
        accession = kwargs["accession"].strip().upper()

        try:
            resp = httpx.get(
                "https://www.ebi.ac.uk/QuickGO/services/annotation/search",
                params={
                    "geneProductId": accession,
                    "limit": "100",
                    "geneProductType": "protein",
                },
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"QuickGO returned {resp.status_code} for {accession}",
                )

            data = resp.json()
            results = data.get("results", [])

            if not results:
                return ToolResult(
                    success=True,
                    data={"accession": accession, "annotations": {}, "total": 0},
                    display=f"No GO annotations found for {accession}",
                )

            grouped: dict[str, list[dict]] = {
                "molecular_function": [],
                "biological_process": [],
                "cellular_component": [],
            }
            seen: set[str] = set()

            for r in results:
                go_id = r.get("goId", "")
                aspect = r.get("goAspect", "").lower().replace(" ", "_")
                if aspect not in grouped or go_id in seen:
                    continue
                seen.add(go_id)
                grouped[aspect].append({
                    "go_id": go_id,
                    "term_name": r.get("goName", ""),
                    "evidence_code": r.get("goEvidence", ""),
                    "qualifier": r.get("qualifier", ""),
                    "assigned_by": r.get("assignedBy", ""),
                })

            counts = {k: len(v) for k, v in grouped.items()}
            total = sum(counts.values())

            display = (
                f"{accession}: {counts.get('molecular_function', 0)} molecular_function, "
                f"{counts.get('biological_process', 0)} biological_process, "
                f"{counts.get('cellular_component', 0)} cellular_component GO terms"
            )
            return ToolResult(
                success=True,
                data={
                    "accession": accession,
                    "total": total,
                    "counts": counts,
                    "annotations": grouped,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
