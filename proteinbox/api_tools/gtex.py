import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class GTExTool(ProteinTool):
    name: str = "gtex"
    description: str = (
        "Query the GTEx Portal for tissue-specific gene expression. "
        "Returns median TPM values across human tissues, showing where "
        "a gene is most highly expressed."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53)",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()

        try:
            # Step 1: Resolve gene symbol to gencodeId
            resp = httpx.get(
                "https://gtexportal.org/api/v2/reference/gene",
                params={"geneId": gene, "datasetId": "gtex_v8"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"GTEx gene lookup returned {resp.status_code} for {gene}",
                )

            gene_data = resp.json().get("data", [])
            if not gene_data:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "tissues": []},
                    display=f"Gene '{gene}' not found in GTEx",
                )

            gencode_id = gene_data[0]["gencodeId"]

            # Step 2: Get median expression across tissues
            resp = httpx.get(
                "https://gtexportal.org/api/v2/expression/medianGeneExpression",
                params={"gencodeId": gencode_id, "datasetId": "gtex_v8"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"GTEx expression query returned {resp.status_code} for {gene}",
                )

            expression_data = resp.json().get("data", [])
            total_tissues = len(expression_data)

            # Sort by median TPM descending, take top 15
            sorted_tissues = sorted(
                expression_data, key=lambda t: t.get("median", 0), reverse=True
            )
            top_tissues = [
                {
                    "tissue": t["tissueSiteDetailId"],
                    "median_tpm": t["median"],
                }
                for t in sorted_tissues[:15]
            ]

            # Build display string
            top_strs = [
                f"{t['tissue']} ({t['median_tpm']:.1f} TPM)" for t in top_tissues[:3]
            ]
            display = (
                f"{gene}: expressed in {total_tissues} tissues, "
                f"top: {', '.join(top_strs)}"
            )

            return ToolResult(
                success=True,
                data={
                    "gene": gene,
                    "gencode_id": gencode_id,
                    "total_tissues": total_tissues,
                    "top_tissues": top_tissues,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
