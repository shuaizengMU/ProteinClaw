import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class WikiPathwaysTool(ProteinTool):
    name: str = "wikipathways"
    description: str = (
        "Search WikiPathways for biological pathways involving a gene or term. "
        "Returns pathway IDs, names, species, and revision dates."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gene symbol or search term (e.g. TP53)",
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()

        try:
            url = "https://www.wikipathways.org/json/findPathwaysByText.json"
            resp = httpx.get(url, params={"query": query}, timeout=30)
            resp.raise_for_status()

            body = resp.json()
            pathways_raw = body.get("result", [])

            if not pathways_raw:
                return ToolResult(
                    success=True,
                    data={"query": query, "pathways": []},
                    display=f"No WikiPathways results for '{query}'",
                )

            pathways = []
            for p in pathways_raw[:20]:
                pathways.append({
                    "id": p.get("id", ""),
                    "name": p.get("name", ""),
                    "species": p.get("species", ""),
                    "revision": p.get("revision", ""),
                    "url": p.get("url", ""),
                })

            total = len(pathways_raw)
            human_pathways = [p for p in pathways if "Homo sapiens" in p.get("species", "")]
            n_human = len(human_pathways)

            first = pathways[0]
            display = (
                f"'{query}': {total} pathways found ({n_human} human). "
                f"Top: {first['name']} ({first['id']}, {first['species']})"
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "total": total,
                    "pathways": pathways,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
