import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class DisProtTool(ProteinTool):
    name: str = "disprot"
    description: str = (
        "Query DisProt for experimentally validated intrinsically disordered protein regions. "
        "Returns disordered region coordinates, evidence types, and experimental methods."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "accession": {
                "type": "string",
                "description": "UniProt accession (e.g. P04637)",
            },
        },
        "required": ["accession"],
    }

    def run(self, **kwargs) -> ToolResult:
        accession = kwargs["accession"].strip().upper()

        try:
            url = "https://disprot.org/api/search"
            resp = httpx.get(url, params={"query": accession, "field": "acc"}, timeout=30)
            resp.raise_for_status()

            body = resp.json()
            results = body.get("data", [])

            if not results:
                return ToolResult(
                    success=True,
                    data={"accession": accession, "regions": []},
                    display=f"No DisProt entry found for {accession}",
                )

            entry = results[0]
            disprot_id = entry.get("disprot_id", "")
            name = entry.get("name", "")
            regions = entry.get("disprot_consensus", {}).get("structural_state", [])

            disorder_regions = []
            for r in regions:
                if r.get("type", "").lower() in ("disorder", "d"):
                    disorder_regions.append({
                        "start": r.get("start"),
                        "end": r.get("end"),
                    })

            # Also collect regions from the regions list directly
            if not disorder_regions:
                for r in entry.get("regions", []):
                    disorder_regions.append({
                        "start": r.get("start"),
                        "end": r.get("end"),
                        "type": r.get("type", ""),
                        "term_name": r.get("term_name", ""),
                    })

            n = len(disorder_regions)
            if n > 0:
                first = disorder_regions[0]
                display = (
                    f"{accession} ({disprot_id}, {name}): "
                    f"{n} disordered region(s). "
                    f"First: {first['start']}-{first['end']}"
                )
            else:
                display = f"{accession} ({disprot_id}, {name}): no disordered regions annotated"

            return ToolResult(
                success=True,
                data={
                    "accession": accession,
                    "disprot_id": disprot_id,
                    "name": name,
                    "disorder_regions": disorder_regions,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
