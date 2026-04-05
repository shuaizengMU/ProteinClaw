import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class UniProtVariantsTool(ProteinTool):
    name: str = "uniprot_variants"
    description: str = (
        "Query the UniProt/EBI Proteins API for known protein variants. "
        "Returns variants with clinical significance, consequence type, "
        "position, and descriptions."
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
            url = f"https://www.ebi.ac.uk/proteins/api/variation/{accession}"
            resp = httpx.get(
                url,
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code == 404:
                return ToolResult(success=False, error=f"No variant data found for {accession}")
            resp.raise_for_status()

            body = resp.json()
            features = body.get("features", [])

            variants = []
            for feat in features[:50]:
                variants.append({
                    "position": feat.get("begin"),
                    "wildtype": feat.get("wildType", ""),
                    "mutant": feat.get("alternativeSequence", ""),
                    "consequence_type": feat.get("consequenceType", ""),
                    "clinical_significance": feat.get("clinicalSignificances", []),
                    "description": feat.get("descriptions", [{}])[0].get("value", "") if feat.get("descriptions") else "",
                    "somaticStatus": feat.get("somaticStatus", 0),
                })

            total = len(features)
            pathogenic = sum(
                1 for v in variants
                if any(
                    cs.get("type", "").lower() in ("pathogenic", "likely pathogenic")
                    for cs in v["clinical_significance"]
                )
            )

            display = (
                f"{accession}: {total} variant(s) total, "
                f"{pathogenic} pathogenic/likely-pathogenic in first {len(variants)}"
            )
            if variants:
                v = variants[0]
                display += f". First: {v['wildtype']}{v['position']}{v['mutant']} ({v['consequence_type']})"

            return ToolResult(
                success=True,
                data={
                    "accession": accession,
                    "total_variants": total,
                    "variants": variants,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
