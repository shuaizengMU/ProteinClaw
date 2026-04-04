import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class AlphaFoldTool(ProteinTool):
    name: str = "alphafold"
    description: str = (
        "Look up a predicted protein structure from AlphaFold DB by UniProt accession. "
        "Returns model URL, mean pLDDT confidence score, sequence coverage, and version."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "uniprot_id": {
                "type": "string",
                "description": "UniProt accession ID, e.g. P04637",
            }
        },
        "required": ["uniprot_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        uniprot_id = kwargs["uniprot_id"].strip().upper()
        url = f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
        try:
            resp = httpx.get(url, timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code == 404:
            return ToolResult(
                success=False,
                error=f"No AlphaFold prediction found for {uniprot_id}",
            )
        if resp.status_code != 200:
            return ToolResult(
                success=False,
                error=f"AlphaFold DB returned {resp.status_code} for {uniprot_id}",
            )

        entries = resp.json()
        if not entries:
            return ToolResult(success=False, error=f"Empty response for {uniprot_id}")

        entry = entries[0]
        data = {
            "uniprot_id": uniprot_id,
            "model_url": entry.get("pdbUrl", ""),
            "cif_url": entry.get("cifUrl", ""),
            "mean_plddt": entry.get("globalMetricValue"),
            "sequence_length": entry.get("uniprotEnd", 0) - entry.get("uniprotStart", 0) + 1,
            "coverage_start": entry.get("uniprotStart"),
            "coverage_end": entry.get("uniprotEnd"),
            "model_version": entry.get("latestVersion"),
            "gene": entry.get("gene", ""),
            "organism": entry.get("organismScientificName", ""),
        }
        plddt = data["mean_plddt"]
        confidence = (
            "Very High" if plddt and plddt >= 90
            else "High" if plddt and plddt >= 70
            else "Low" if plddt and plddt >= 50
            else "Very Low" if plddt
            else "Unknown"
        )
        display = (
            f"AlphaFold {uniprot_id}: pLDDT={plddt} ({confidence}), "
            f"{data['sequence_length']} residues, v{data['model_version']}"
        )
        return ToolResult(success=True, data=data, display=display)
