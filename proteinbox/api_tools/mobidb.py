import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class MobiDBTool(ProteinTool):
    name: str = "mobidb"
    description: str = (
        "Query MobiDB for protein intrinsic disorder annotations. "
        "Returns disorder consensus regions, curated disorder annotations, "
        "protein length, and organism."
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
            url = "https://mobidb.org/api/download"
            resp = httpx.get(url, params={"acc": accession, "format": "json"}, timeout=30)
            resp.raise_for_status()

            data = resp.json()

            # MobiDB may return a list or a single object
            if isinstance(data, list):
                if not data:
                    return ToolResult(success=False, error=f"No MobiDB entry found for {accession}")
                entry = data[0]
            else:
                entry = data

            length = entry.get("length")
            organism = entry.get("organism", "unknown")

            # Collect consensus disorder regions
            consensus_regions = []
            features = entry.get("mobidb_consensus", {}).get("disorder", {}).get("consensus", [])
            for feat in features:
                start = feat.get("start")
                end = feat.get("end")
                if start is not None and end is not None:
                    consensus_regions.append({"start": start, "end": end})

            # Collect curated disorder annotations
            curated = []
            curated_feats = entry.get("curated-disorder-experimentally_defined", [])
            for feat in curated_feats:
                start = feat.get("start")
                end = feat.get("end")
                src = feat.get("source", "")
                if start is not None and end is not None:
                    curated.append({"start": start, "end": end, "source": src})

            n_consensus = len(consensus_regions)
            n_curated = len(curated)

            if n_consensus > 0:
                first = consensus_regions[0]
                display = (
                    f"{accession} ({organism}): {length} aa, "
                    f"{n_consensus} consensus disorder region(s), "
                    f"{n_curated} curated annotation(s). "
                    f"First disorder: {first['start']}-{first['end']}"
                )
            else:
                display = (
                    f"{accession} ({organism}): {length} aa, "
                    f"no consensus disorder regions found, "
                    f"{n_curated} curated annotation(s)"
                )

            return ToolResult(
                success=True,
                data={
                    "accession": accession,
                    "length": length,
                    "organism": organism,
                    "consensus_disorder_regions": consensus_regions,
                    "curated_disorder": curated,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
