import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class PANTHERTool(ProteinTool):
    name: str = "panther"
    description: str = (
        "Classify a protein into PANTHER families and subfamilies. "
        "Returns protein family, subfamily, protein class, and GO slim annotations. "
        "Useful for understanding evolutionary relationships and functional classification."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53) or UniProt accession (e.g. P04637)",
            },
            "organism": {
                "type": "string",
                "description": "NCBI taxon ID. Default: 9606 (human)",
                "default": "9606",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip()
        organism = kwargs.get("organism", "9606").strip()

        try:
            resp = httpx.get(
                "https://pantherdb.org/services/oai/pantherdb/geneinfo",
                params={
                    "geneInputList": gene,
                    "organism": organism,
                },
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"PANTHER returned {resp.status_code} for {gene}",
                )

            data = resp.json()
            mapped = data.get("search", {}).get("mapped_genes", {})
            gene_list = mapped.get("gene", []) if mapped else []
            if isinstance(gene_list, dict):
                gene_list = [gene_list]

            if not gene_list:
                return ToolResult(
                    success=False,
                    error=f"No PANTHER classification found for '{gene}'",
                )

            results = []
            for g in gene_list[:5]:
                ann = g.get("annotation_type_list", {}).get("annotation_data_type", [])
                if isinstance(ann, dict):
                    ann = [ann]
                go_terms = []
                for a in ann:
                    content = a.get("content", "")
                    ann_type = a.get("annotation_type", "")
                    if content:
                        go_terms.append({
                            "type": ann_type,
                            "content": content,
                        })

                panther_family = g.get("persistent_id", "")
                family_name = g.get("family_name", "")
                subfamily_name = g.get("subfamily_name", "")
                protein_class = g.get("protein_class", "")

                results.append({
                    "accession": g.get("accession", ""),
                    "gene_symbol": g.get("gene_symbol", ""),
                    "gene_name": g.get("gene_name", ""),
                    "panther_family_id": panther_family,
                    "family_name": family_name,
                    "subfamily_name": subfamily_name,
                    "protein_class": protein_class,
                    "species": g.get("species", ""),
                    "go_annotations": go_terms[:10],
                })

            top = results[0] if results else {}
            display = (
                f"{top.get('gene_symbol', gene)}: "
                f"{top.get('family_name', 'Unknown family')} ({top.get('panther_family_id', '')})"
            )
            if top.get("protein_class"):
                display += f", class: {top['protein_class']}"

            return ToolResult(success=True, data={"gene": gene, "results": results}, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
