import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class InterProTool(ProteinTool):
    name: str = "interpro"
    description: str = (
        "Look up protein domain and family annotations from InterPro by UniProt accession. "
        "Returns domain hits from Pfam, PROSITE, CDD, and other member databases "
        "with coordinates and descriptions."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "uniprot_id": {
                "type": "string",
                "description": "UniProt accession ID, e.g. P04637",
            }
        },
        "required": ["uniprot_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        uniprot_id = kwargs["uniprot_id"].strip().upper()
        url = f"https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/UniProt/{uniprot_id}"
        try:
            resp = httpx.get(url, timeout=30, headers={"Accept": "application/json"})
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code != 200:
            return ToolResult(
                success=False,
                error=f"InterPro returned {resp.status_code} for {uniprot_id}",
            )

        raw = resp.json()
        results = raw.get("results", [])

        domains = []
        for entry in results:
            meta = entry.get("metadata", {})
            # Extract coordinates from protein locations
            locations = []
            for protein in entry.get("proteins", []):
                for loc_group in protein.get("entry_protein_locations", []):
                    for frag in loc_group.get("fragments", []):
                        locations.append({
                            "start": frag.get("start"),
                            "end": frag.get("end"),
                        })

            domains.append({
                "accession": meta.get("accession", ""),
                "name": meta.get("name", ""),
                "type": meta.get("type", ""),
                "source_database": meta.get("source_database", ""),
                "locations": locations,
            })

        data = {
            "uniprot_id": uniprot_id,
            "domain_count": len(domains),
            "domains": domains[:20],  # cap for LLM context
        }
        display = f"{uniprot_id}: {len(domains)} InterPro domain(s) found"
        return ToolResult(success=True, data=data, display=display)
