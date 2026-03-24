# tests/proteinbox/test_uniprot.py
import pytest
import respx
import httpx
from proteinbox.tools.uniprot import UniProtTool

MOCK_RESPONSE = {
    "primaryAccession": "P04637",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Cellular tumor antigen p53"}}
    },
    "comments": [
        {"commentType": "FUNCTION", "texts": [{"value": "Acts as a tumor suppressor."}]}
    ],
    "genes": [{"geneName": {"value": "TP53"}}],
    "organism": {"scientificName": "Homo sapiens"},
    "sequence": {"length": 393},
    "uniProtKBCrossReferences": [
        {"database": "GO", "id": "GO:0003677", "properties": [
            {"key": "GoTerm", "value": "F:DNA binding"}
        ]}
    ],
}

@respx.mock
def test_uniprot_tool_success():
    respx.get("https://rest.uniprot.org/uniprotkb/P04637.json").mock(
        return_value=httpx.Response(200, json=MOCK_RESPONSE)
    )
    tool = UniProtTool()
    result = tool.run(accession_id="P04637")
    assert result.success is True
    assert result.data["accession"] == "P04637"
    assert result.data["name"] == "Cellular tumor antigen p53"
    assert result.data["organism"] == "Homo sapiens"
    assert result.data["sequence_length"] == 393
    assert "TP53" in result.data["genes"]
    assert result.display is not None

@respx.mock
def test_uniprot_tool_not_found():
    respx.get("https://rest.uniprot.org/uniprotkb/INVALID.json").mock(
        return_value=httpx.Response(404)
    )
    tool = UniProtTool()
    result = tool.run(accession_id="INVALID")
    assert result.success is False
    assert "404" in result.error or "not found" in result.error.lower()

@respx.mock
def test_uniprot_tool_registered():
    from proteinbox.tools.registry import TOOL_REGISTRY
    import importlib
    import proteinbox.tools.uniprot  # noqa: F401 — triggers registration
    assert "uniprot" in TOOL_REGISTRY
