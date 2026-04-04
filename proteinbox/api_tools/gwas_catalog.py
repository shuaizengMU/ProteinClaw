import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class GWASCatalogTool(ProteinTool):
    name: str = "gwas_catalog"
    description: str = (
        "Search the NHGRI-EBI GWAS Catalog for genome-wide association study results. "
        "Given a gene symbol, returns associated traits/diseases with SNP rsIDs, "
        "p-values, risk alleles, and study references. "
        "Useful for understanding population-level genetic associations."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. BRCA1, TP53, APOE)",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()

        try:
            resp = httpx.get(
                "https://www.ebi.ac.uk/gwas/rest/api/associations/search/findByGene",
                params={"geneName": gene},
                headers={"Accept": "application/json"},
                timeout=30,
            )

            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    error=f"GWAS Catalog returned {resp.status_code} for {gene}",
                )

            data = resp.json()
            associations_raw = (
                data.get("_embedded", {}).get("associations", [])
            )

            if not associations_raw:
                return ToolResult(
                    success=True,
                    data={"gene": gene, "associations": [], "total": 0},
                    display=f"No GWAS associations found for {gene}",
                )

            associations = []
            for a in associations_raw[:20]:
                traits = [
                    t.get("trait", "")
                    for t in a.get("efoTraits", a.get("traits", []))
                ]
                if not traits:
                    traits = [a.get("diseaseTrait", {}).get("trait", "")]

                snps = []
                for locus in a.get("loci", []):
                    for sra in locus.get("strongestRiskAlleles", []):
                        snps.append(sra.get("riskAlleleName", ""))

                p_mantissa = a.get("pvalueMantissa", 0)
                p_exponent = a.get("pvalueExponent", 0)
                if p_mantissa and p_exponent:
                    p_str = f"{p_mantissa}e{p_exponent}"
                else:
                    p_str = str(a.get("pvalue", 0))

                associations.append({
                    "traits": traits,
                    "snps": snps,
                    "p_value": p_str,
                    "risk_frequency": a.get("riskFrequency", ""),
                    "or_beta": a.get("orPerCopyNum", a.get("betaNum", "")),
                    "study_accession": a.get("studyAccession", ""),
                })

            all_traits: list[str] = []
            for a in associations:
                for t in a["traits"]:
                    if t and t not in all_traits:
                        all_traits.append(t)

            display = (
                f"{gene}: {len(associations_raw)} GWAS associations — "
                + ", ".join(all_traits[:5])
            )

            return ToolResult(
                success=True,
                data={
                    "gene": gene,
                    "total": len(associations_raw),
                    "associations": associations,
                    "unique_traits": all_traits,
                },
                display=display,
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))
