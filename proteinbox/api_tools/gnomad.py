import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool

GNOMAD_CONSTRAINT_QUERY = """
query GeneConstraint($symbol: String!) {
  gene(gene_symbol: $symbol, reference_genome: GRCh38) {
    gene_id
    symbol
    gnomad_constraint {
      pli
      lof_z
      mis_z
      syn_z
    }
  }
}
""".strip()


@register_tool
class GnomADTool(ProteinTool):
    name: str = "gnomad"
    description: str = (
        "Query gnomAD for gene-level variant constraint metrics and top loss-of-function "
        "variants. Returns pLI score, LOEUF (loss-of-function observed/expected upper "
        "fraction), and missense constraint."
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
            url = "https://gnomad.broadinstitute.org/api"
            resp = httpx.post(url, json={
                "query": GNOMAD_CONSTRAINT_QUERY,
                "variables": {"symbol": gene},
            }, timeout=30)
            resp.raise_for_status()

            body = resp.json()
            gene_data = body.get("data", {}).get("gene")

            if not gene_data:
                return ToolResult(success=False, error=f"No gnomAD data found for gene {gene}")

            gene_id = gene_data.get("gene_id", "")
            symbol = gene_data.get("symbol", gene)
            constraint = gene_data.get("gnomad_constraint")

            if constraint is None:
                display = f"{symbol} ({gene_id}): constraint data not available"
                data = {
                    "gene_id": gene_id,
                    "symbol": symbol,
                    "constraint": None,
                }
                return ToolResult(success=True, data=data, display=display)

            pli = constraint.get("pli")
            lof_z = constraint.get("lof_z")
            mis_z = constraint.get("mis_z")
            syn_z = constraint.get("syn_z")

            def fmt(val):
                return f"{val:.2f}" if val is not None else "N/A"

            display = f"{symbol} ({gene_id}): pLI={fmt(pli)}, lof_z={fmt(lof_z)}, mis_z={fmt(mis_z)}"

            data = {
                "gene_id": gene_id,
                "symbol": symbol,
                "constraint": {
                    "pli": pli,
                    "lof_z": lof_z,
                    "mis_z": mis_z,
                    "syn_z": syn_z,
                },
            }

            return ToolResult(success=True, data=data, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
