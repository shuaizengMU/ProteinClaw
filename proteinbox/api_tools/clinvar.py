import time
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class ClinVarTool(ProteinTool):
    name: str = "clinvar"
    description: str = (
        "Search ClinVar for clinical significance of genetic variants associated with a gene. "
        "Returns variant names, clinical significance (pathogenic/benign/VUS), conditions, "
        "and review status. Useful for understanding disease-associated mutations."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. BRCA1, TP53)",
            },
            "significance": {
                "type": "string",
                "description": "Filter by clinical significance: pathogenic, benign, uncertain, or all. Default: pathogenic",
                "default": "pathogenic",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()
        significance = kwargs.get("significance", "pathogenic").strip().lower()

        sig_filter = ""
        if significance == "pathogenic":
            sig_filter = ' AND "clinsig pathogenic"[Properties]'
        elif significance == "benign":
            sig_filter = ' AND "clinsig benign"[Properties]'

        try:
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            resp = httpx.get(search_url, params={
                "db": "clinvar",
                "term": f"{gene}[gene]{sig_filter}",
                "retmode": "json",
                "retmax": "20",
            }, timeout=30)
            resp.raise_for_status()
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
            total = int(resp.json().get("esearchresult", {}).get("count", 0))

            if not ids:
                return ToolResult(success=False, error=f"No ClinVar entries found for gene {gene}")

            # NCBI rate-limits to ~3 req/s without an API key; pause to avoid 429
            time.sleep(0.4)
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            resp = httpx.get(summary_url, params={
                "db": "clinvar", "id": ",".join(ids[:10]), "retmode": "json",
            }, timeout=30)
            resp.raise_for_status()
            result = resp.json().get("result", {})

            variants = []
            for vid in ids[:10]:
                info = result.get(vid, {})
                variants.append({
                    "variation_id": vid,
                    "title": info.get("title", ""),
                    "clinical_significance": info.get("clinical_significance", {}).get("description", ""),
                    "conditions": [
                        t.get("trait_name", "")
                        for t in info.get("trait_set", [])
                    ],
                    "review_status": info.get("clinical_significance", {}).get("review_status", ""),
                    "variation_type": info.get("variation_set", [{}])[0].get("variation_type", "") if info.get("variation_set") else "",
                })

            display = f"Found {total} ClinVar entries for {gene}. Showing top {len(variants)}."
            return ToolResult(success=True, data={"gene": gene, "total": total, "variants": variants}, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
