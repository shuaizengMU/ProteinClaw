import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class PDBTool(ProteinTool):
    name: str = "pdb"
    description: str = (
        "Look up a protein structure in the RCSB Protein Data Bank by PDB ID. "
        "Returns title, experimental method, resolution, organism, deposit date, "
        "number of chains, and ligand names."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "pdb_id": {
                "type": "string",
                "description": "PDB identifier, e.g. 1TUP, 6LU7",
            }
        },
        "required": ["pdb_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        pdb_id = kwargs["pdb_id"].strip().upper()
        url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
        try:
            resp = httpx.get(url, timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, error=str(e))

        if resp.status_code != 200:
            return ToolResult(
                success=False,
                error=f"RCSB PDB returned {resp.status_code} for {pdb_id}",
            )

        raw = resp.json()

        title = raw.get("struct", {}).get("title", "Unknown")
        method = raw.get("exptl", [{}])[0].get("method", "Unknown")
        resolution = None
        for r in raw.get("rcsb_entry_info", {}).get("resolution_combined", []) or []:
            resolution = r
            break
        deposit_date = raw.get("rcsb_accession_info", {}).get("deposit_date", "Unknown")
        organism_list = [
            src.get("ncbi_scientific_name", "Unknown")
            for src in raw.get("rcsb_entity_source_organism", [])
        ]
        organism = ", ".join(set(organism_list)) if organism_list else "Unknown"
        polymer_count = raw.get("rcsb_entry_info", {}).get("polymer_entity_count", 0)

        # Ligands from nonpolymer entities
        ligands = []
        for ne in raw.get("rcsb_entry_info", {}).get("nonpolymer_bound_components", []) or []:
            ligands.append(ne)

        data = {
            "pdb_id": pdb_id,
            "title": title,
            "method": method,
            "resolution_angstrom": resolution,
            "deposit_date": deposit_date,
            "organism": organism,
            "polymer_chains": polymer_count,
            "ligands": ligands[:10],
        }
        res_str = f"{resolution} Å" if resolution else "N/A"
        display = f"{pdb_id}: {title[:80]} — {method}, {res_str}, {organism}"
        return ToolResult(success=True, data=data, display=display)
