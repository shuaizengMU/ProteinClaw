import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class HumanProteinAtlasTool(ProteinTool):
    name: str = "protein_atlas"
    description: str = (
        "Query the Human Protein Atlas for tissue and cell expression, "
        "subcellular localization, and protein classification. "
        "Returns RNA expression across tissues, protein detection via IHC, "
        "and where in the cell the protein is found."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53, EGFR, BRCA1)",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()

        try:
            resp = httpx.get(
                f"https://www.proteinatlas.org/{gene}.json",
                timeout=30,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"Human Protein Atlas returned {resp.status_code} for {gene}",
                )

            raw = resp.json()
            if isinstance(raw, list):
                raw = raw[0] if raw else {}

            gene_name = raw.get("Gene", gene)
            gene_desc = raw.get("Gene description", "")
            protein_class = raw.get("Protein class", [])
            if isinstance(protein_class, str):
                protein_class = [protein_class]

            subcellular = raw.get("Subcellular location", [])
            if isinstance(subcellular, str):
                subcellular = [subcellular]

            rna_tissue = raw.get("RNA tissue specificity", "")
            rna_data = raw.get("RNA tissue distribution", "")

            tissue_expr = raw.get("Tissue expression cluster", [])
            if isinstance(tissue_expr, str):
                tissue_expr = [tissue_expr]

            cancer_specificity = raw.get("RNA cancer specificity", "")
            prognostic = raw.get("Prognostic - favorable", [])
            if isinstance(prognostic, str):
                prognostic = [prognostic]

            data = {
                "gene": gene_name,
                "description": gene_desc,
                "protein_class": protein_class,
                "subcellular_localization": subcellular,
                "rna_tissue_specificity": rna_tissue,
                "rna_tissue_distribution": rna_data,
                "tissue_expression_cluster": tissue_expr,
                "cancer_specificity": cancer_specificity,
                "prognostic_favorable": prognostic,
                "url": f"https://www.proteinatlas.org/{gene}",
            }

            loc_str = ", ".join(subcellular[:5]) if subcellular else "unknown"
            class_str = ", ".join(protein_class[:3]) if protein_class else "unclassified"
            display = (
                f"{gene_name}: localization: {loc_str}, "
                f"class: {class_str}"
            )
            if cancer_specificity:
                display += f", cancer specificity: {cancer_specificity}"

            return ToolResult(success=True, data=data, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
