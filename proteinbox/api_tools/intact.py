import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class IntActTool(ProteinTool):
    name: str = "intact"
    description: str = (
        "Query IntAct for curated molecular interactions. "
        "Given a UniProt accession, returns binary protein interactions with "
        "experimental detection methods, interaction types, and confidence scores. "
        "Complements STRING with curated, experimentally validated interactions."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "accession": {
                "type": "string",
                "description": "UniProt accession ID (e.g. P04637 for TP53)",
            },
        },
        "required": ["accession"],
    }

    def run(self, **kwargs) -> ToolResult:
        accession = kwargs["accession"].strip().upper()

        try:
            resp = httpx.get(
                f"https://www.ebi.ac.uk/intact/ws/interaction/findInteractor/{accession}",
                params={"pageSize": "25"},
                headers={"Accept": "application/json"},
                timeout=30,
            )

            if resp.status_code == 404:
                return ToolResult(
                    success=True,
                    data={"accession": accession, "interactions": [], "total": 0},
                    display=f"No IntAct interactions found for {accession}",
                )

            if resp.status_code != 200:
                resp = httpx.get(
                    "https://www.ebi.ac.uk/intact/ws/interaction/list",
                    params={"query": accession, "pageSize": "25"},
                    headers={"Accept": "application/json"},
                    timeout=30,
                )
                if resp.status_code != 200:
                    return ToolResult(
                        success=False,
                        error=f"IntAct returned {resp.status_code} for {accession}",
                    )

            data = resp.json()
            content = data.get("content", data) if isinstance(data, dict) else data
            if isinstance(content, dict):
                content = content.get("data", [content])

            interactions = []
            for item in (content if isinstance(content, list) else [])[:20]:
                partners = []
                for p in item.get("participants", item.get("interactors", [])):
                    acc = p.get("interactorRef", p.get("accession", ""))
                    name = p.get("preferredName", p.get("name", ""))
                    if acc != accession:
                        partners.append({"accession": acc, "name": name})

                interactions.append({
                    "interaction_id": item.get("ac", item.get("interactionAc", "")),
                    "partners": partners,
                    "interaction_type": item.get("interactionType", {}).get("shortName", ""),
                    "detection_method": item.get("detectionMethod", {}).get("shortName", ""),
                    "publication_count": item.get("publicationCount", 0),
                    "mi_score": item.get("miScore", item.get("intactMiscore", 0)),
                })

            total = data.get("totalElements", len(interactions)) if isinstance(data, dict) else len(interactions)

            top_partners = []
            for i in interactions[:5]:
                for p in i.get("partners", []):
                    if p.get("name"):
                        top_partners.append(p["name"])

            display = f"{accession}: {total} interactions"
            if top_partners:
                display += f", top partners: {', '.join(top_partners[:5])}"

            return ToolResult(
                success=True,
                data={"accession": accession, "total": total, "interactions": interactions},
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
