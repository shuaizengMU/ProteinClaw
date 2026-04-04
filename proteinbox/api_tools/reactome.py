import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class ReactomeTool(ProteinTool):
    name: str = "reactome"
    description: str = (
        "Query Reactome pathway database for biological pathways associated with a protein or gene. "
        "Returns pathway names, species, diagram availability, and sub-pathways. "
        "Complements KEGG with more detailed human pathway and reaction information."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53) or UniProt accession (e.g. P04637)",
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()
        base = "https://reactome.org/ContentService"

        try:
            # Try as UniProt accession first, then gene symbol
            resp = httpx.get(
                f"{base}/data/pathways/low/entity/UniProt:{query}",
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                resp = httpx.get(
                    f"{base}/search/query?query={query}&types=Protein&cluster=true",
                    headers={"Accept": "application/json"},
                    timeout=30,
                )
                resp.raise_for_status()
                search = resp.json()
                entries = search.get("results", [{}])[0].get("entries", [])
                if not entries:
                    return ToolResult(success=False, error=f"No Reactome results for '{query}'")

                stable_id = entries[0].get("stId", "")
                resp = httpx.get(
                    f"{base}/data/pathways/low/entity/{stable_id}",
                    headers={"Accept": "application/json"},
                    timeout=30,
                )

            if resp.status_code != 200:
                return ToolResult(success=False, error=f"Reactome returned {resp.status_code}")

            pathways_raw = resp.json()
            pathways = []
            for p in pathways_raw[:15]:
                pathways.append({
                    "stable_id": p.get("stId", ""),
                    "name": p.get("displayName", ""),
                    "species": p.get("species", [{}])[0].get("displayName", "") if p.get("species") else "",
                    "has_diagram": p.get("hasDiagram", False),
                    "url": f"https://reactome.org/content/detail/{p.get('stId', '')}",
                })

            display = f"Found {len(pathways_raw)} Reactome pathways for {query}. Showing top {len(pathways)}."
            return ToolResult(success=True, data={"query": query, "total": len(pathways_raw), "pathways": pathways}, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
