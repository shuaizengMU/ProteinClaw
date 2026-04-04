import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

KEGG_BASE = "https://rest.kegg.jp"


@register_tool
class KEGGTool(ProteinTool):
    name: str = "kegg"
    description: str = (
        "Look up KEGG pathway information for a gene. "
        "Input a KEGG gene ID (e.g. hsa:7157 for human TP53) or search by gene name. "
        "Returns pathways the gene participates in."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "KEGG gene ID (e.g. hsa:7157) or search term (e.g. 'TP53 human')",
            }
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()

        # If it looks like a KEGG gene ID (org:id), use it directly
        if ":" in query and len(query.split(":")[0]) <= 4:
            gene_id = query
        else:
            # Search for the gene
            gene_id = self._find_gene(query)
            if gene_id is None:
                return ToolResult(
                    success=False,
                    error=f"No KEGG gene found for '{query}'",
                )

        # Get pathway links for this gene
        try:
            resp = httpx.get(f"{KEGG_BASE}/link/pathway/{gene_id}", timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code != 200 or not resp.text.strip():
            return ToolResult(
                success=False,
                error=f"No pathways found for {gene_id}",
            )

        pathway_ids = []
        for line in resp.text.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) == 2:
                pathway_ids.append(parts[1].replace("path:", ""))

        if not pathway_ids:
            return ToolResult(success=False, error=f"No pathways for {gene_id}")

        # Get pathway names
        pathways = []
        for pid in pathway_ids[:15]:  # cap
            name = self._get_pathway_name(pid)
            pathways.append({
                "pathway_id": pid,
                "name": name,
                "url": f"https://www.kegg.jp/pathway/{pid}",
            })

        data = {
            "gene_id": gene_id,
            "pathway_count": len(pathways),
            "pathways": pathways,
        }
        top = pathways[0]["name"] if pathways else "none"
        display = f"{gene_id}: {len(pathways)} KEGG pathways. Top: {top}"
        return ToolResult(success=True, data=data, display=display)

    def _find_gene(self, query: str) -> str | None:
        try:
            resp = httpx.get(f"{KEGG_BASE}/find/genes/{query}", timeout=30)
        except httpx.RequestError:
            return None
        if resp.status_code != 200 or not resp.text.strip():
            return None
        first_line = resp.text.strip().split("\n")[0]
        return first_line.split("\t")[0] if "\t" in first_line else None

    def _get_pathway_name(self, pathway_id: str) -> str:
        try:
            resp = httpx.get(f"{KEGG_BASE}/get/{pathway_id}", timeout=15)
        except httpx.RequestError:
            return pathway_id
        for line in resp.text.split("\n"):
            if line.startswith("NAME"):
                return line.replace("NAME", "").strip().rstrip(" - Homo sapiens (human)")
        return pathway_id
