import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class CATHTool(ProteinTool):
    name: str = "cath"
    description: str = (
        "Query the CATH database for structural domain classification. "
        "Given a UniProt accession, returns CATH domain assignments with "
        "Class, Architecture, Topology, and Homologous superfamily hierarchy. "
        "Useful for understanding protein structural organization and fold families."
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
                f"https://www.cathdb.info/version/current/api/rest/uniprot/{accession}",
                headers={"Accept": "application/json"},
                timeout=30,
            )

            if resp.status_code == 404:
                return ToolResult(
                    success=True,
                    data={"accession": accession, "domains": []},
                    display=f"No CATH structural domains found for {accession}",
                )

            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"CATH returned {resp.status_code} for {accession}",
                )

            raw = resp.json()
            domain_list = raw if isinstance(raw, list) else raw.get("data", [raw])

            domains = []
            for d in domain_list[:10]:
                cath_id = d.get("cath_id", d.get("superfamily_id", ""))
                domains.append({
                    "domain_id": d.get("domain_id", d.get("name", "")),
                    "cath_id": cath_id,
                    "class": d.get("class_name", ""),
                    "architecture": d.get("architecture_name", ""),
                    "topology": d.get("topology_name", ""),
                    "superfamily": d.get("superfamily_name", d.get("homology_name", "")),
                    "start": d.get("start", ""),
                    "end": d.get("end", ""),
                    "resolution": d.get("resolution", ""),
                })

            if not domains:
                return ToolResult(
                    success=True,
                    data={"accession": accession, "domains": []},
                    display=f"No CATH structural domains found for {accession}",
                )

            domain_strs = [
                f"{d['cath_id']} ({d['class']}, {d['architecture']})"
                if d.get("class") else d.get("cath_id", "unknown")
                for d in domains[:3]
            ]
            display = f"{accession}: {len(domains)} CATH domains — {', '.join(domain_strs)}"

            return ToolResult(
                success=True,
                data={"accession": accession, "domains": domains},
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
