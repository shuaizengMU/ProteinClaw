import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class OpenTargetsTool(ProteinTool):
    name: str = "opentargets"
    description: str = (
        "Query Open Targets Platform for target-disease associations. "
        "Given a gene symbol, returns top disease associations with evidence scores, "
        "known drugs, and tractability assessments. Aggregates evidence from genetics, "
        "somatic mutations, drugs, literature, and more."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "gene": {
                "type": "string",
                "description": "Gene symbol (e.g. EGFR, TP53, BRCA1)",
            },
        },
        "required": ["gene"],
    }

    def run(self, **kwargs) -> ToolResult:
        gene = kwargs["gene"].strip().upper()
        api = "https://api.platform.opentargets.org/api/v4/graphql"

        try:
            # Step 1: Resolve gene symbol to Ensembl ID
            search_query = {
                "query": """
                query SearchTarget($q: String!) {
                    search(queryString: $q, entityNames: ["target"], page: {size: 1, index: 0}) {
                        hits { id name }
                    }
                }
                """,
                "variables": {"q": gene},
            }
            resp = httpx.post(api, json=search_query, timeout=30)
            resp.raise_for_status()
            hits = resp.json().get("data", {}).get("search", {}).get("hits", [])

            if not hits:
                return ToolResult(success=False, error=f"No Open Targets target found for '{gene}'")

            ensembl_id = hits[0]["id"]
            target_name = hits[0].get("name", gene)

            # Step 2: Get disease associations + known drugs
            assoc_query = {
                "query": """
                query TargetAssoc($id: String!) {
                    target(ensemblId: $id) {
                        approvedName
                        approvedSymbol
                        knownDrugs(size: 10) {
                            rows {
                                drug { name }
                                phase
                                mechanismOfAction
                                disease { name }
                            }
                        }
                        associatedDiseases(page: {size: 15, index: 0}) {
                            rows {
                                disease { id name }
                                score
                                datasourceScores {
                                    componentId: id
                                    score
                                }
                            }
                        }
                    }
                }
                """,
                "variables": {"id": ensembl_id},
            }
            resp = httpx.post(api, json=assoc_query, timeout=30)
            resp.raise_for_status()
            target = resp.json().get("data", {}).get("target", {})

            if not target:
                return ToolResult(success=False, error=f"No data returned for {ensembl_id}")

            assoc_rows = target.get("associatedDiseases", {}).get("rows", [])
            associations = []
            for row in assoc_rows:
                disease = row.get("disease", {})
                ds_scores = {
                    s.get("componentId", ""): round(s.get("score", 0), 3)
                    for s in row.get("datasourceScores", [])
                }
                associations.append({
                    "disease_id": disease.get("id", ""),
                    "disease_name": disease.get("name", ""),
                    "overall_score": round(row.get("score", 0), 3),
                    "datatype_scores": ds_scores,
                })

            drug_rows = target.get("knownDrugs", {}).get("rows", [])
            drugs = []
            for d in drug_rows:
                drugs.append({
                    "drug_name": d.get("drug", {}).get("name", ""),
                    "phase": d.get("phase", ""),
                    "mechanism": d.get("mechanismOfAction", ""),
                    "indication": d.get("disease", {}).get("name", ""),
                })

            data = {
                "gene": gene,
                "ensembl_id": ensembl_id,
                "approved_name": target.get("approvedName", ""),
                "associations": associations,
                "drugs": drugs,
                "total_associations": len(assoc_rows),
            }

            top_disease = associations[0]["disease_name"] if associations else "none"
            top_score = associations[0]["overall_score"] if associations else 0
            display = (
                f"{gene} ({ensembl_id}): {len(associations)} disease associations, "
                f"top: {top_disease} ({top_score}), {len(drugs)} known drugs"
            )
            return ToolResult(success=True, data=data, display=display)

        except Exception as e:
            return ToolResult(success=False, error=str(e))
