import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class OMIMTool(ProteinTool):
    name: str = "omim"
    description: str = (
        "Search OMIM (Online Mendelian Inheritance in Man) for genetic disease associations. "
        "Given a gene symbol, returns associated Mendelian diseases, inheritance patterns, "
        "and phenotype descriptions. Uses NCBI as the data source (no OMIM API key required)."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. BRCA1, CFTR, TP53)",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()

        try:
            # Step 1: Find the NCBI Gene ID
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            resp = httpx.get(search_url, params={
                "db": "gene",
                "term": f"{gene}[Gene Name] AND Homo sapiens[Organism]",
                "retmode": "json",
                "retmax": "1",
            }, timeout=30)
            resp.raise_for_status()
            gene_ids = resp.json().get("esearchresult", {}).get("idlist", [])

            if not gene_ids:
                return ToolResult(success=False, error=f"Gene '{gene}' not found in NCBI Gene")

            gene_id = gene_ids[0]

            # Step 2: Link Gene → OMIM
            link_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
            resp = httpx.get(link_url, params={
                "dbfrom": "gene", "db": "omim", "id": gene_id, "retmode": "json",
            }, timeout=30)
            resp.raise_for_status()

            omim_ids = []
            for ls in resp.json().get("linksets", []):
                for ldb in ls.get("linksetdbs", []):
                    omim_ids.extend([str(x) for x in ldb.get("links", [])])

            if not omim_ids:
                return ToolResult(success=True, data={"gene": gene, "diseases": [], "note": "No OMIM entries linked"}, display=f"No OMIM disease entries found for {gene}")

            # Step 3: Fetch OMIM summaries
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            resp = httpx.get(summary_url, params={
                "db": "omim", "id": ",".join(omim_ids[:15]), "retmode": "json",
            }, timeout=30)
            resp.raise_for_status()
            result = resp.json().get("result", {})

            diseases = []
            for oid in omim_ids[:15]:
                info = result.get(oid, {})
                title = info.get("title", "")
                # OMIM titles use format: "GENE SYMBOL; DISORDER NAME"
                diseases.append({
                    "omim_id": oid,
                    "title": title,
                    "url": f"https://omim.org/entry/{oid}",
                })

            display = f"Found {len(omim_ids)} OMIM entries for {gene}. Showing {len(diseases)}."
            return ToolResult(success=True, data={"gene": gene, "gene_id": gene_id, "diseases": diseases}, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
