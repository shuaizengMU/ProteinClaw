import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class NCBIGeneTool(ProteinTool):
    name: str = "ncbi_gene"
    description: str = (
        "Search NCBI Gene (Entrez Gene) for gene information by gene symbol or name. "
        "Returns gene ID, official symbol, full name, summary, organism, aliases, "
        "and cross-references to other databases. Useful for ID mapping and gene overview."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53), name, or NCBI Gene ID",
            },
            "organism": {
                "type": "string",
                "description": "Organism filter, e.g. 'human' or 'Homo sapiens'. Default: human",
                "default": "human",
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()
        organism = kwargs.get("organism", "human").strip()
        search_term = f"{query}[Gene Name] AND {organism}[Organism]"

        try:
            # Search for gene ID
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            resp = httpx.get(search_url, params={
                "db": "gene", "term": search_term, "retmode": "json", "retmax": "5",
            }, timeout=30)
            resp.raise_for_status()
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                # Fallback: search without gene name field
                resp = httpx.get(search_url, params={
                    "db": "gene", "term": f"{query} AND {organism}[Organism]",
                    "retmode": "json", "retmax": "5",
                }, timeout=30)
                resp.raise_for_status()
                ids = resp.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return ToolResult(success=False, error=f"No gene found for '{query}' in {organism}")

            # Fetch gene summary
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            resp = httpx.get(summary_url, params={
                "db": "gene", "id": ",".join(ids[:3]), "retmode": "json",
            }, timeout=30)
            resp.raise_for_status()
            result = resp.json().get("result", {})

            genes = []
            for gid in ids[:3]:
                info = result.get(gid, {})
                genes.append({
                    "gene_id": gid,
                    "symbol": info.get("name", ""),
                    "full_name": info.get("description", ""),
                    "organism": info.get("organism", {}).get("scientificname", ""),
                    "aliases": info.get("otheraliases", ""),
                    "summary": info.get("summary", "")[:500],
                    "chromosome": info.get("chromosome", ""),
                    "map_location": info.get("maplocation", ""),
                })

            top = genes[0] if genes else {}
            display = (
                f"{top.get('symbol', '?')} (Gene ID: {top.get('gene_id', '?')}) — "
                f"{top.get('full_name', '?')}, {top.get('organism', '?')}, "
                f"Chr {top.get('chromosome', '?')}{top.get('map_location', '')}"
            )
            return ToolResult(success=True, data=genes, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
