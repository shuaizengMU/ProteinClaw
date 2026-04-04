import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class DisGeNETTool(ProteinTool):
    name: str = "disgenet"
    description: str = (
        "Query DisGeNET for disease-gene associations. "
        "Returns diseases associated with a gene (or genes associated with a disease), "
        "with association scores and evidence sources. "
        "Useful for understanding clinical relevance of proteins."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53) or disease name (e.g. 'breast cancer')",
            },
            "search_type": {
                "type": "string",
                "description": "'gene' to find diseases for a gene, 'disease' to find genes for a disease. Default: gene",
                "default": "gene",
                "enum": ["gene", "disease"],
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()
        search_type = kwargs.get("search_type", "gene").strip().lower()
        base = "https://www.disgenet.org/api"

        try:
            if search_type == "gene":
                resp = httpx.get(
                    f"{base}/gda/gene/{query}",
                    params={"source": "ALL", "format": "json"},
                    headers={"Accept": "application/json"},
                    timeout=30,
                )
            else:
                resp = httpx.get(
                    f"{base}/gda/disease/{query}",
                    params={"source": "ALL", "format": "json"},
                    headers={"Accept": "application/json"},
                    timeout=30,
                )

            if resp.status_code == 404 or resp.status_code == 400:
                # Fallback: use the search endpoint
                resp = httpx.get(
                    f"{base}/gda/search/{query}",
                    params={"source": "ALL", "format": "json"},
                    headers={"Accept": "application/json"},
                    timeout=30,
                )

            if resp.status_code != 200:
                # DisGeNET API may require auth; fall back to NCBI MedGen
                return self._fallback_ncbi(query, search_type)

            results = resp.json()
            if not results:
                return self._fallback_ncbi(query, search_type)

            associations = []
            for item in results[:15]:
                associations.append({
                    "gene_symbol": item.get("gene_symbol", ""),
                    "disease_name": item.get("disease_name", ""),
                    "score": item.get("score", 0),
                    "ei": item.get("ei", 0),
                    "el": item.get("el", ""),
                    "n_pmids": item.get("pmid_count", 0) or item.get("npmids", 0),
                })

            display = f"Found {len(results)} disease-gene associations for '{query}'. Showing top {len(associations)}."
            return ToolResult(success=True, data={"query": query, "total": len(results), "associations": associations}, display=display)

        except Exception:
            return self._fallback_ncbi(query, search_type)

    def _fallback_ncbi(self, query: str, search_type: str) -> ToolResult:
        """Fallback to NCBI Gene2MIM / PubMed for disease-gene associations."""
        try:
            search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            if search_type == "gene":
                term = f"{query}[Gene Name] AND Homo sapiens[Organism]"
                db = "gene"
            else:
                term = f"{query}"
                db = "medgen"

            resp = httpx.get(search_url, params={
                "db": db, "term": term, "retmode": "json", "retmax": "5",
            }, timeout=30)
            resp.raise_for_status()
            ids = resp.json().get("esearchresult", {}).get("idlist", [])

            if not ids:
                return ToolResult(success=False, error=f"No disease-gene associations found for '{query}'")

            # Use elink to find related disease/gene records
            link_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
            target_db = "omim" if search_type == "gene" else "gene"
            resp = httpx.get(link_url, params={
                "dbfrom": db, "db": target_db, "id": ids[0], "retmode": "json",
            }, timeout=30)
            resp.raise_for_status()
            linksets = resp.json().get("linksets", [])

            linked_ids = []
            for ls in linksets:
                for ldb in ls.get("linksetdbs", []):
                    linked_ids.extend([str(x) for x in ldb.get("links", [])[:10]])

            if not linked_ids:
                return ToolResult(success=True, data={"query": query, "note": "No linked disease/gene records found via NCBI"}, display=f"No disease associations found for '{query}' via NCBI")

            # Fetch summaries
            summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            resp = httpx.get(summary_url, params={
                "db": target_db, "id": ",".join(linked_ids[:10]), "retmode": "json",
            }, timeout=30)
            resp.raise_for_status()
            result = resp.json().get("result", {})

            associations = []
            for lid in linked_ids[:10]:
                info = result.get(lid, {})
                associations.append({
                    "id": lid,
                    "title": info.get("title", info.get("description", "")),
                    "source": "NCBI",
                })

            display = f"Found {len(associations)} related records for '{query}' via NCBI."
            return ToolResult(success=True, data={"query": query, "associations": associations, "source": "NCBI fallback"}, display=display)

        except Exception as e:
            return ToolResult(success=False, error=f"DisGeNET and NCBI fallback both failed: {e}")
