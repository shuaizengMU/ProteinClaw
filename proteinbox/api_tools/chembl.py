import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class ChEMBLTool(ProteinTool):
    name: str = "chembl"
    description: str = (
        "Search ChEMBL for drug-target interactions. Given a protein target (gene symbol or UniProt ID), "
        "returns approved drugs, clinical candidates, and bioactive compounds with their mechanisms of action. "
        "Useful for drug discovery and understanding therapeutic relevance of proteins."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gene symbol (e.g. EGFR) or UniProt accession (e.g. P00533)",
            },
        },
        "required": ["query"],
    }

    def run(self, **kwargs) -> ToolResult:
        query = kwargs["query"].strip()
        base = "https://www.ebi.ac.uk/chembl/api/data"

        try:
            # Search for target
            resp = httpx.get(
                f"{base}/target/search.json",
                params={"q": query, "limit": "5"},
                timeout=30,
            )
            resp.raise_for_status()
            targets = resp.json().get("targets", [])

            if not targets:
                return ToolResult(success=False, error=f"No ChEMBL target found for '{query}'")

            target = targets[0]
            target_chembl_id = target.get("target_chembl_id", "")
            target_name = target.get("pref_name", "")
            target_type = target.get("target_type", "")

            # Get approved drugs via drug mechanisms
            resp = httpx.get(
                f"{base}/mechanism.json",
                params={"target_chembl_id": target_chembl_id, "limit": "20"},
                timeout=30,
            )
            resp.raise_for_status()
            mechanisms = resp.json().get("mechanisms", [])

            drugs = []
            for mech in mechanisms[:15]:
                mol_id = mech.get("molecule_chembl_id", "")
                # Fetch molecule info
                mol_resp = httpx.get(f"{base}/molecule/{mol_id}.json", timeout=15)
                mol_data = mol_resp.json() if mol_resp.status_code == 200 else {}

                drugs.append({
                    "molecule_chembl_id": mol_id,
                    "molecule_name": mol_data.get("pref_name", mech.get("molecule_chembl_id", "")),
                    "mechanism_of_action": mech.get("mechanism_of_action", ""),
                    "action_type": mech.get("action_type", ""),
                    "max_phase": mol_data.get("max_phase", ""),
                    "molecule_type": mol_data.get("molecule_type", ""),
                    "first_approval": mol_data.get("first_approval"),
                })

            # Get bioactivity count
            act_resp = httpx.get(
                f"{base}/activity.json",
                params={"target_chembl_id": target_chembl_id, "limit": "1"},
                timeout=15,
            )
            activity_count = 0
            if act_resp.status_code == 200:
                activity_count = act_resp.json().get("page_meta", {}).get("total_count", 0)

            data = {
                "target_chembl_id": target_chembl_id,
                "target_name": target_name,
                "target_type": target_type,
                "drugs": drugs,
                "total_bioactivities": activity_count,
            }

            approved = [d for d in drugs if d.get("max_phase") == 4]
            display = (
                f"{target_name} ({target_chembl_id}): "
                f"{len(approved)} approved drugs, {len(drugs)} total drug mechanisms, "
                f"{activity_count} bioactivity records"
            )
            return ToolResult(success=True, data=data, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
