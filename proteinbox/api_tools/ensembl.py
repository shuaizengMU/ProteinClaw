import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class EnsemblTool(ProteinTool):
    name: str = "ensembl"
    description: str = (
        "Query Ensembl for genomic information about a gene or protein. "
        "Returns Ensembl gene/transcript IDs, genomic coordinates, biotype, "
        "orthologs, and cross-references. Useful for genomic context and cross-species comparison."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Gene symbol (e.g. TP53, BRCA1)",
            },
            "species": {
                "type": "string",
                "description": "Species name, e.g. 'human' or 'mouse'. Default: human",
                "default": "human",
            },
        },
        "required": ["symbol"],
    }

    def run(self, **kwargs) -> ToolResult:
        symbol = kwargs["symbol"].strip()
        species = kwargs.get("species", "human").strip().lower()
        base = "https://rest.ensembl.org"

        try:
            # Lookup gene by symbol
            resp = httpx.get(
                f"{base}/lookup/symbol/{species}/{symbol}",
                params={"expand": "1", "content-type": "application/json"},
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if resp.status_code != 200:
                return ToolResult(success=False, error=f"Ensembl: gene '{symbol}' not found in {species}")

            gene = resp.json()
            gene_id = gene.get("id", "")

            data = {
                "gene_id": gene_id,
                "display_name": gene.get("display_name", ""),
                "description": gene.get("description", ""),
                "biotype": gene.get("biotype", ""),
                "species": gene.get("species", ""),
                "assembly": gene.get("assembly_name", ""),
                "chromosome": gene.get("seq_region_name", ""),
                "start": gene.get("start"),
                "end": gene.get("end"),
                "strand": gene.get("strand"),
                "transcripts": [],
            }

            for t in gene.get("Transcript", [])[:5]:
                data["transcripts"].append({
                    "transcript_id": t.get("id", ""),
                    "display_name": t.get("display_name", ""),
                    "biotype": t.get("biotype", ""),
                    "is_canonical": t.get("is_canonical", 0) == 1,
                    "length": t.get("length"),
                })

            # Fetch orthologs
            try:
                orth_resp = httpx.get(
                    f"{base}/homology/id/{gene_id}",
                    params={"type": "orthologues", "content-type": "application/json"},
                    headers={"Accept": "application/json"},
                    timeout=30,
                )
                if orth_resp.status_code == 200:
                    homologies = orth_resp.json().get("data", [{}])[0].get("homologies", [])
                    orthologs = []
                    seen = set()
                    for h in homologies:
                        target = h.get("target", {})
                        sp = target.get("species", "")
                        if sp not in seen and len(orthologs) < 10:
                            seen.add(sp)
                            orthologs.append({
                                "species": sp,
                                "gene_id": target.get("id", ""),
                                "protein_id": target.get("protein_id", ""),
                                "perc_id": target.get("perc_id"),
                            })
                    data["orthologs"] = orthologs
            except Exception:
                data["orthologs"] = []

            display = (
                f"{data['display_name']} ({gene_id}) — {data['species']}, "
                f"Chr{data['chromosome']}:{data['start']}-{data['end']}, "
                f"{len(data['transcripts'])} transcripts, {len(data.get('orthologs', []))} orthologs"
            )
            return ToolResult(success=True, data=data, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
