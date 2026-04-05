import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class CBioPortalTool(ProteinTool):
    name: str = "cbioportal"
    description: str = (
        "Query cBioPortal for cancer genomics data. Returns gene information "
        "(Entrez ID, type, cytoband) available across 535+ cancer studies."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53, BRCA1)",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()

        try:
            url = f"https://www.cbioportal.org/api/genes/{gene}"
            resp = httpx.get(url, headers={"Accept": "application/json"}, timeout=30)

            if resp.status_code == 404:
                return ToolResult(success=False, error=f"Gene '{gene}' not found in cBioPortal")
            resp.raise_for_status()

            gene_info = resp.json()

            entrez_id = gene_info.get("entrezGeneId")
            hugo_symbol = gene_info.get("hugoGeneSymbol", gene)
            gene_type = gene_info.get("type", "")
            cytoband = gene_info.get("cytoband", "")
            length = gene_info.get("length")

            display = (
                f"{hugo_symbol} (Entrez: {entrez_id}): type={gene_type}, "
                f"cytoband={cytoband}"
            )
            if length:
                display += f", length={length} bp"

            return ToolResult(
                success=True,
                data={
                    "hugo_symbol": hugo_symbol,
                    "entrez_gene_id": entrez_id,
                    "type": gene_type,
                    "cytoband": cytoband,
                    "length": length,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
