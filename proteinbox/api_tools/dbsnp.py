import time
import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class DbSNPTool(ProteinTool):
    name: str = "dbsnp"
    description: str = (
        "Query NCBI dbSNP for SNP details by rsID. Returns genomic position, alleles, "
        "clinical significance, associated gene, and global minor allele frequency."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "rsid": {
                "type": "string",
                "description": "dbSNP rsID (e.g. rs7412, rs429358)",
            },
        },
        "required": ["rsid"],
    }

    def run(self, **kwargs) -> ToolResult:
        rsid = kwargs["rsid"].strip().lower()
        if rsid.startswith("rs"):
            rsid_number = rsid[2:]
        else:
            rsid_number = rsid

        try:
            # NCBI rate-limits to ~3 req/s without an API key; pause to avoid 429
            time.sleep(0.4)
            url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            resp = httpx.get(url, params={
                "db": "snp",
                "id": rsid_number,
                "retmode": "json",
            }, timeout=30)
            resp.raise_for_status()

            result = resp.json().get("result", {})
            snp_data = result.get(rsid_number, {})

            if not snp_data or "error" in snp_data:
                return ToolResult(success=False, error=f"No dbSNP entry found for rs{rsid_number}")

            snp_id = snp_data.get("snp_id", rsid_number)
            snp_class = snp_data.get("snp_class", "")
            chrpos = snp_data.get("chrpos", "")
            clinical_significance = snp_data.get("clinical_significance", "")

            genes = snp_data.get("genes", [])
            gene_names = [g.get("name", "") for g in genes if g.get("name")]

            global_mafs = snp_data.get("global_mafs", [])
            maf_entries = []
            for m in global_mafs:
                freq = m.get("freq", "")
                study = m.get("study", "")
                if freq or study:
                    maf_entries.append({"freq": freq, "study": study})

            top_maf = maf_entries[0]["freq"] if maf_entries else "N/A"
            gene_str = ", ".join(gene_names) if gene_names else "unknown"
            clin_str = clinical_significance if clinical_significance else "not reported"

            # Build chromosome position string
            if chrpos:
                parts = chrpos.split(":")
                pos_display = f"Chr{parts[0]}:{parts[1]}" if len(parts) == 2 else chrpos
            else:
                pos_display = "unknown"

            display = f"rs{snp_id}: {gene_str}, {pos_display}, MAF={top_maf}, clinical: {clin_str}"

            data = {
                "snp_id": snp_id,
                "snp_class": snp_class,
                "chrpos": chrpos,
                "genes": gene_names,
                "global_mafs": maf_entries,
                "clinical_significance": clinical_significance,
            }

            return ToolResult(success=True, data=data, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
