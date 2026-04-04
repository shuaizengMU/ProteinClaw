import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class STRINGTool(ProteinTool):
    name: str = "string"
    description: str = (
        "Query the STRING database for protein-protein interaction partners. "
        "Input a protein name (e.g. TP53) and species taxid (default 9606 for human). "
        "Returns top interaction partners with combined scores."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "protein_name": {
                "type": "string",
                "description": "Protein or gene name, e.g. TP53, BRCA1",
            },
            "species": {
                "type": "integer",
                "description": "NCBI taxonomy ID (default: 9606 for Homo sapiens)",
                "default": 9606,
            },
            "limit": {
                "type": "integer",
                "description": "Max number of interaction partners (default: 10)",
                "default": 10,
            },
        },
        "required": ["protein_name"],
    }

    def run(self, **kwargs) -> ToolResult:
        protein = kwargs["protein_name"].strip()
        species = int(kwargs.get("species", 9606))
        limit = int(kwargs.get("limit", 10))

        url = "https://string-db.org/api/json/network"
        params = {
            "identifiers": protein,
            "species": species,
            "limit": limit,
            "caller_identity": "proteinclaw",
        }
        try:
            resp = httpx.get(url, params=params, timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code != 200:
            return ToolResult(
                success=False,
                error=f"STRING returned {resp.status_code}",
            )

        entries = resp.json()
        if not entries:
            return ToolResult(
                success=False,
                error=f"No interactions found for {protein} (species {species})",
            )

        partners = []
        seen = set()
        for e in entries:
            a = e.get("preferredName_A", "")
            b = e.get("preferredName_B", "")
            partner = b if a.upper() == protein.upper() else a
            if partner in seen:
                continue
            seen.add(partner)
            partners.append({
                "partner": partner,
                "combined_score": e.get("score", 0),
                "nscore": e.get("nscore", 0),
                "fscore": e.get("fscore", 0),
                "pscore": e.get("pscore", 0),
                "ascore": e.get("ascore", 0),
                "escore": e.get("escore", 0),
                "dscore": e.get("dscore", 0),
                "tscore": e.get("tscore", 0),
            })

        partners.sort(key=lambda x: x["combined_score"], reverse=True)

        data = {
            "query": protein,
            "species": species,
            "partner_count": len(partners),
            "partners": partners[:limit],
        }
        top3 = ", ".join(p["partner"] for p in partners[:3])
        display = f"{protein}: {len(partners)} interaction partners. Top: {top3}"
        return ToolResult(success=True, data=data, display=display)
