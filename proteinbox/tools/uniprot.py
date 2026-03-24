import httpx
from proteinbox.tools.registry import ProteinTool, ToolResult, register_tool


@register_tool
class UniProtTool(ProteinTool):
    name: str = "uniprot"
    description: str = (
        "Query UniProt for protein information by accession ID. "
        "Returns protein name, function, gene names, organism, sequence length, and GO terms."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "accession_id": {
                "type": "string",
                "description": "UniProt accession ID, e.g. P04637",
            }
        },
        "required": ["accession_id"],
    }

    def run(self, **kwargs) -> ToolResult:
        accession_id = kwargs["accession_id"].strip().upper()
        url = f"https://rest.uniprot.org/uniprotkb/{accession_id}.json"
        try:
            response = httpx.get(url, timeout=30)
        except httpx.RequestError as e:
            return ToolResult(success=False, data=None, error=str(e))

        if response.status_code != 200:
            return ToolResult(
                success=False,
                data=None,
                error=f"UniProt returned {response.status_code} for accession {accession_id}",
            )

        raw = response.json()

        # Extract fields
        name = (
            raw.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value", "Unknown")
        )
        genes = [
            g["geneName"]["value"]
            for g in raw.get("genes", [])
            if "geneName" in g
        ]
        organism = raw.get("organism", {}).get("scientificName", "Unknown")
        seq_length = raw.get("sequence", {}).get("length", 0)
        function_texts = [
            t["value"]
            for c in raw.get("comments", [])
            if c.get("commentType") == "FUNCTION"
            for t in c.get("texts", [])
        ]
        go_terms = [
            next((p["value"] for p in ref.get("properties", []) if p["key"] == "GoTerm"), ref["id"])
            for ref in raw.get("uniProtKBCrossReferences", [])
            if ref.get("database") == "GO"
        ]

        data = {
            "accession": accession_id,
            "name": name,
            "genes": genes,
            "organism": organism,
            "sequence_length": seq_length,
            "function": function_texts,
            "go_terms": go_terms[:10],  # cap at 10 for LLM context
        }
        display = (
            f"{name} ({', '.join(genes) or 'no gene name'}) — {organism}, "
            f"{seq_length} aa. Function: {function_texts[0][:200] if function_texts else 'N/A'}"
        )
        return ToolResult(success=True, data=data, display=display)
